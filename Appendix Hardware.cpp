#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <ArduinoOTA.h>
#include <time.h> 

// --- NETWORK CONFIGURATION ---
const char* ssid = "SunwayEdu-MainCampus";
const char* password = "";
const char* targetIP = "172.20.88.125"; 
const int targetPort = 8000;      // MATLAB listens here for sensor telemetry (unchanged)
const int listenPort = 8001;      // this ESP32 listens here for buzz commands FROM MATLAB

// --- OTA CONFIGURATION ---
const char* otaHostname = "shm-sensor-esp32";   // shows up under this name in Arduino IDE's Network Port list
const char* otaPassword = "CHANGE_ME_SHM_2026"; // change this - required since the network is shared

// --- NTP TIME CONFIGURATION ---
const char* ntpServer = "pool.ntp.org";
const long  gmtOffset_sec = 8 * 3600; 
const int   daylightOffset_sec = 0;  

WiFiUDP udp;   // used for both sending telemetry and receiving buzz commands

// --- SENSOR & BUZZER CONFIGURATION ---
int ADXL345 = 0x53; 
float X_out, Y_out, Z_out;
int X_offset = 0, Y_offset = 0, Z_offset = 0;

const int VIB_SENSOR_PIN = 12; 
const int BUZZER_PIN = 14;     

// ==========================================================
// Non-blocking remote buzz pattern (driven by MATLAB's
// STA/LTA detector via UDP). millis()-based so it never calls
// delay() and never stalls the sensor/UDP streaming loop.
// ==========================================================
bool patternActive = false;
unsigned long patternStepStart = 0;
int patternStepIndex = 0;
const int* patternSteps = nullptr;
int patternStepCount = 0;

// Step lists alternate ON,OFF,ON,OFF... durations in ms.
const int MOTOR_START_PATTERN[] = {150};                                   // one short beep
const int COLLAPSE_PATTERN[]    = {120,100,120,100,120,100,120,100,120};   // 5 fast beeps

void startPattern(const int steps[], int count) {
  patternSteps = steps;
  patternStepCount = count;
  patternStepIndex = 0;
  patternStepStart = millis();
  patternActive = true;
}

bool patternWantsBuzzerOn() {
  return patternActive && (patternStepIndex % 2 == 0);
}

void updatePattern() {
  if (!patternActive) return;
  if (millis() - patternStepStart >= (unsigned long)patternSteps[patternStepIndex]) {
    patternStepIndex++;
    patternStepStart = millis();
    if (patternStepIndex >= patternStepCount) {
      patternActive = false;
    }
  }
}

void checkForBuzzCommand() {
  int packetSize = udp.parsePacket();
  if (packetSize <= 0) return;

  char cmdBuf[48] = {0};
  int len = udp.read(cmdBuf, sizeof(cmdBuf) - 1);
  if (len <= 0) return;
  cmdBuf[len] = 0;
  String cmd = String(cmdBuf);

  Serial.print("[BUZZ CMD] ");
  Serial.println(cmd);

  if (cmd.indexOf("COLLAPSE") != -1) {
    startPattern(COLLAPSE_PATTERN, sizeof(COLLAPSE_PATTERN) / sizeof(int));
  } else if (cmd.indexOf("MOTOR START") != -1 || cmd.indexOf("MOTOR_START") != -1) {
    startPattern(MOTOR_START_PATTERN, sizeof(MOTOR_START_PATTERN) / sizeof(int));
  }
}
// ==========================================================

// ==========================================================
// NEW: OTA firmware update support (wireless reflashing)
// ==========================================================
void setupOTA() {
  ArduinoOTA.setHostname(otaHostname);
  ArduinoOTA.setPassword(otaPassword);

  ArduinoOTA.onStart([]() {
    String type = (ArduinoOTA.getCommand() == U_FLASH) ? "sketch" : "filesystem";
    Serial.println("OTA update starting: " + type);
    // Force the buzzer off and cancel any in-flight pattern so it can't
    // get stuck ON if the update fails partway through.
    patternActive = false;
    digitalWrite(BUZZER_PIN, LOW);
  });
  ArduinoOTA.onEnd([]() {
    Serial.println("\nOTA update complete - rebooting");
  });
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    Serial.printf("OTA progress: %u%%\r", (progress * 100) / total);
  });
  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("OTA error [%u]: ", error);
    if (error == OTA_AUTH_ERROR)         Serial.println("Auth failed");
    else if (error == OTA_BEGIN_ERROR)   Serial.println("Begin failed");
    else if (error == OTA_CONNECT_ERROR) Serial.println("Connect failed");
    else if (error == OTA_RECEIVE_ERROR) Serial.println("Receive failed");
    else if (error == OTA_END_ERROR)     Serial.println("End failed");
  });

  ArduinoOTA.begin();
  Serial.print("OTA ready. Hostname: ");
  Serial.println(otaHostname);
}
// ==========================================================

void calibrateADXL345() {
  float numReadings = 500;
  float xSum = 0, ySum = 0, zSum = 0;
  
  Serial.println("Beginning Calibration... Do not touch sensor!");
  
  for (int i = 0; i < numReadings; i++) {
    Wire.beginTransmission(ADXL345);
    Wire.write(0x32);
    Wire.endTransmission(false);
    Wire.requestFrom(ADXL345, 6, true);
    
    int16_t raw_X = (Wire.read() | Wire.read() << 8);
    int16_t raw_Y = (Wire.read() | Wire.read() << 8);
    int16_t raw_Z = (Wire.read() | Wire.read() << 8);
    
    xSum += raw_X;
    ySum += raw_Y;
    zSum += raw_Z;
  }
  
  X_offset = (0 - (xSum / numReadings)) / 2;
  Y_offset = (0 - (ySum / numReadings)) / 2;
  Z_offset = (128 - (zSum / numReadings)) / 2; 
  
  Wire.beginTransmission(ADXL345);
  Wire.write(0x1E); Wire.write(X_offset);
  Wire.endTransmission();
  
  Wire.beginTransmission(ADXL345);
  Wire.write(0x1F); Wire.write(Y_offset);
  Wire.endTransmission();
  
  Wire.beginTransmission(ADXL345);
  Wire.write(0x20); Wire.write(Z_offset);
  Wire.endTransmission();
  
  Serial.println("Calibration Complete.");
}

void configureADXL345() {
  Wire.beginTransmission(ADXL345);
  Wire.write(0x2D); 
  Wire.write(8);    
  Wire.endTransmission();
  delay(10);

  Wire.beginTransmission(ADXL345);
  Wire.write(0x31); 
  Wire.write(0x01); // +/- 4G Range, 10-bit mode (128 LSB/g)
  Wire.endTransmission();
  delay(10);

  // SPEED HACK 1: Set ADXL345 internal sampling rate to 200 Hz
  Wire.beginTransmission(ADXL345);
  Wire.write(0x2C); 
  Wire.write(0x0B); 
  Wire.endTransmission();
  delay(10);
}

void setup() {
  // hardware limit kept at 9600
  Serial.begin(9600); 
  
  Wire.begin();
  // SPEED HACK 2: Fast I2C communication (400kHz)
  Wire.setClock(400000); 

  // Initialize SW-420 and Buzzer pins
  pinMode(VIB_SENSOR_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW); // Ensure buzzer is silent on startup
  
  // Connect to Wi-Fi
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
  Serial.print("This ESP32's IP address (put this in esp32IP in MATLAB): ");
  Serial.println(WiFi.localIP());

  // Bind so this device can receive buzz commands on listenPort,
  // while still being able to send telemetry to targetIP:targetPort below.
  udp.begin(listenPort);
  Serial.print("Listening for buzz commands on UDP port ");
  Serial.println(listenPort);

  // NEW: bring up OTA once Wi-Fi is confirmed connected
  setupOTA();

  // Configure Time
  Serial.print("Fetching actual time...");
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  struct tm timeinfo;
  while (!getLocalTime(&timeinfo)) {
    Serial.print(".");
    delay(500);
  }
  Serial.println("\nTime synced successfully!");

  // Setup Sensor
  configureADXL345();
  calibrateADXL345(); 

  // MATLAB FIX: 3-second gap ensures MATLAB detects a "New Batch"
  Serial.println("--- READY! DATA STREAM STARTING IN 3 SECONDS ---");
  delay(3000); 
}

void loop() {
  // 0. NEW: service any pending OTA update request (cheap no-op when idle;
  //    blocks for the duration of an actual flash, which is expected).
  ArduinoOTA.handle();

  // 1. Check for an incoming buzz command from MATLAB's STA/LTA detector,
  //    and advance the non-blocking beep pattern.
  checkForBuzzCommand();
  updatePattern();

  // 2. Read SW-420 Vibration state (1 = Vibrating, 0 = Not Vibrating)
  int isVibrating = digitalRead(VIB_SENSOR_PIN);
  
  // 3. Drive the buzzer: ON if EITHER the raw SW-420 switch is tripped
  //    OR a remote STA/LTA pattern is currently mid-beep.
  bool buzzerShouldBeOn = (isVibrating == HIGH) || patternWantsBuzzerOn();
  digitalWrite(BUZZER_PIN, buzzerShouldBeOn ? HIGH : LOW);

  // 4. Read ADXL345 Sensor Data
  Wire.beginTransmission(ADXL345);
  Wire.write(0x32); 
  Wire.endTransmission(false);
  Wire.requestFrom(ADXL345, 6, true);
  
  int16_t raw_X = (Wire.read() | Wire.read() << 8);
  int16_t raw_Y = (Wire.read() | Wire.read() << 8);
  int16_t raw_Z = (Wire.read() | Wire.read() << 8);
  
  X_out = ((float)raw_X / 128.0) * 9.81;
  Y_out = ((float)raw_Y / 128.0) * 9.81;
  Z_out = ((float)raw_Z / 128.0) * 9.81;

  // 5. Get formatted time
  struct tm timeinfo;
  char timeString[25]; 
  if(!getLocalTime(&timeinfo)){
    sprintf(timeString, "TimeError");
  } else {
    strftime(timeString, sizeof(timeString), "%Y-%m-%d %H:%M:%S", &timeinfo);
  }

  // 6. Build the UDP Payload (unchanged format)
  String payload = String(timeString) + "," + String(X_out, 2) + "," + String(Y_out, 2) + "," + String(Z_out, 2) + "," + String(isVibrating);
  
  // 7. Send over UDP (unchanged)
  udp.beginPacket(targetIP, targetPort);
  udp.print(payload);
  udp.endPacket();

  // Print to Serial for debugging
  Serial.println(payload);
  
  // SPEED HACK 4: Minimal delay to keep loop tight
  delay(2); 
}
