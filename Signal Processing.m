% =========================================================================
% MATLAB Script: SHM Pipeline (Ultimate Master Edition v11.0 - SMS Merged)
% Features: 3-Axis Global / X-Axis Deep Dive / STFT / STA-LTA / Variance
% INCLUDES: Full Educational FFTs + Dynamic Threshold Calibration + Hilbert Viz
%           + SMS Alert Gateway (fires for ALL 3 payloads: 10kg, 8kg, 6kg)
% =========================================================================
clear; clc; close all;
%% ==========================================
% GLOBAL AESTHETICS (DARK THEME DASHBOARD)
% ==========================================
% Applies dark mode to all figures generated in this pipeline
set(groot, 'defaultFigureColor', [0.1 0.1 0.1]);
set(groot, 'defaultAxesColor', 'k');
set(groot, 'defaultAxesXColor', 'w');
set(groot, 'defaultAxesYColor', 'w');
set(groot, 'defaultAxesZColor', 'w');
set(groot, 'defaultTextColor', 'w');
set(groot, 'defaultAxesGridColor', [0.3 0.3 0.3]);
set(groot, 'defaultAxesGridAlpha', 0.8);
%% ==========================================
% SMS ALERT GATEWAY CONFIGURATION
% ==========================================
smsEnabled  = true;                    % master switch - set false to disable all SMS sending
phoneIP     = '172.20.10.4';           % IP shown on your Flutter app screen
targetPhone = '+60189637332';          % phone number to receive the SMS (with country code)
smsURL      = sprintf('http://%s:8080/sendsms', phoneIP);
smsOptions  = weboptions('MediaType', 'application/json', ...
                          'RequestMethod', 'post', ...
                          'Timeout', 10);

function sendCollapseSMS(smsEnabled, smsURL, smsOptions, eventType, currentName, targetPhone)
% Sends an SMS alert for a detected MOTOR START, CRACK, or COLLAPSE
% (earthquake) event.
% Wrapped in try/catch so a failed SMS never stops the MATLAB pipeline.
% Called for every payload (10kg, 8kg, 6kg) since the calling loop in
% Part 6A runs across ALL THREE datasets - no payload is skipped.
%
% Message wording:
%   MOTOR START -> "Earthquake nearby the bridge"
%   CRACK       -> "Crack detected nearby the bridge"
%   COLLAPSE    -> "HIGH earthquake nearby the bridge"

    if ~smsEnabled
        return;
    end

    switch eventType
        case 'MOTOR START'
            msg = sprintf('ALERT!! Earthquake nearby the bridge [%s]', currentName);

        case 'CRACK'
            msg = sprintf('ALERT!! Crack detected nearby the bridge [%s]', currentName);

        case 'COLLAPSE'
            msg = sprintf('ALERT!! HIGH earthquake nearby the bridge [%s]', currentName);

        otherwise
            msg = sprintf('ALERT!! %s nearby the bridge [%s]', eventType, currentName);
    end

    % IMPORTANT: the phone/Flutter server expects BOTH 'phone' and 'message'
    % fields in the JSON body - omitting 'phone' causes a Dart null-cast
    % error server-side ("type 'Null' is not a subtype of type 'String'").
    payload = struct('phone', targetPhone, 'message', msg);

    try
        response = webwrite(smsURL, payload, smsOptions);
        fprintf('  [SMS SENT] %s\n', msg);
    catch err
        fprintf('  [SMS FAILED] %s | Reason: %s\n', msg, err.message);
    end
end

function sendBuzzerCommand(buzzerEnabled, udpObj, eventType, esp32_IP, esp32_Port)
% Sends a UDP command string to the ESP32 to trigger the physical buzzer.
% Mirrors the live-monitoring buzzer logic in SHM_LiveMonitor.m (Phase 0),
% but fires from the OFFLINE STA/LTA multi-event detector in Part 6A
% instead of a live streaming loop.
%
% Wrapped in try/catch so a failed UDP write never stops the MATLAB
% pipeline - same defensive pattern as sendCollapseSMS above.
%
% eventType is forwarded as the literal UDP payload string sent to the
% ESP32 ('MOTOR START', 'CRACK', or 'COLLAPSE'). The ESP32 firmware is
% expected to switch its buzz pattern based on this string, the same way
% it does in the live monitor script. If your current ESP32 sketch only
% recognizes 'MOTOR START' and 'COLLAPSE' (as in SHM_LiveMonitor.m
% Phase 0), CRACK events will still be sent as the literal text "CRACK"
% and will simply be ignored by that firmware until you add a case for
% it - update the ESP32 sketch to add a distinct buzz pattern for CRACK
% if you want it to react differently from MOTOR START / COLLAPSE.

    if ~buzzerEnabled || isempty(udpObj)
        return;
    end

    try
        write(udpObj, string(eventType), "string", esp32_IP, esp32_Port);
        fprintf('  [BUZZ SENT] %s -> %s:%d\n', eventType, esp32_IP, esp32_Port);
    catch err
        fprintf('  [BUZZ FAILED] %s | Reason: %s\n', eventType, err.message);
    end
end

function [pks, locs] = detectTriggerEvents(ratio, triggerOnLevel, triggerOffLevel)
% ADAPTIVE replacement for findpeaks(..., 'MinPeakDistance', fixed_seconds).
%
% Implements a classic STA/LTA trigger/de-trigger state machine (in the
% spirit of Allen 1978 / Trnkoczy 2012 NMSOP-2 Ch.8): once the ratio
% crosses ABOVE triggerOnLevel, an event is "latched" and its running
% peak value/index is tracked. The event only closes - and only THEN
% gets recorded as one entry in pks/locs - once the ratio drops back
% BELOW triggerOffLevel. A new event cannot begin until the previous one
% has fully de-triggered.
%
% This removes the hand-picked MinPeakDistance-in-seconds parameter
% entirely. Event separation is now determined by the signal itself
% returning toward baseline, not by a fixed time window - so a tight
% cluster of ringdown peaks that never drops back to baseline is
% correctly treated as ONE event, while genuinely separate events (ratio
% dips back to baseline in between) are correctly split into several.
%
% triggerOnLevel  - e.g. Critical_Threshold (Steady_State_Baseline * Deviation_Tolerance)
% triggerOffLevel - e.g. Steady_State_Baseline (the calibrated quiet-window level)

    pks = [];
    locs = [];
    inEvent = false;
    peakVal = -Inf;
    peakIdx = NaN;

    for idx = 1:length(ratio)
        val = ratio(idx);
        if ~inEvent
            if val >= triggerOnLevel
                inEvent = true;
                peakVal = val;
                peakIdx = idx;
            end
        else
            if val > peakVal
                peakVal = val;
                peakIdx = idx;
            end
            if val <= triggerOffLevel
                pks(end+1) = peakVal;   %#ok<AGROW>
                locs(end+1) = peakIdx;  %#ok<AGROW>
                inEvent = false;
                peakVal = -Inf;
                peakIdx = NaN;
            end
        end
    end

    % If the recording ends while still above triggerOffLevel (event
    % never de-triggered before data ran out), close it out anyway so it
    % isn't silently dropped.
    if inEvent
        pks(end+1) = peakVal;
        locs(end+1) = peakIdx;
    end

    pks = pks(:);
    locs = locs(:);
end
%% ==========================================
% ESP32 BUZZER GATEWAY CONFIGURATION
% ==========================================
% Fires alongside sendCollapseSMS() in Part 6A - same three event types
% (MOTOR START / CRACK / COLLAPSE), sent as UDP text commands instead of
% an HTTP POST. Uses the same one-way "fire and forget" pattern as the
% live monitor's Phase 0 buzzer trigger, just driven by the offline
% STA/LTA detector's trigger/de-trigger events instead of a live loop.
buzzerEnabled = true;                  % master switch - set false to disable all buzzer UDP sends
esp32_IP      = '192.168.0.123';       % <--- MUST MATCH your ESP32's IP address
esp32_Port    = 8001;                  % port the ESP32 listens on for buzz commands

try
    buzzerUdpObj = udpport("datagram", "IPv4");
    fprintf('[BUZZER] UDP sender ready -> will target %s:%d\n', esp32_IP, esp32_Port);
catch err
    buzzerUdpObj = [];
    buzzerEnabled = false;
    fprintf('[BUZZER] WARNING: Could not open UDP port (%s). Buzzer alerts disabled for this run.\n', err.message);
end
%% ==========================================
% USER INPUT: Define Your Test Sets (currently 6 total)
% ==========================================
% NOTE: datasetDates is now PER-ROW because the two batches of tests were
% recorded on different dates. Row order must match timeLimits/datasetNames.
datasetDates = {
    '2026-05-25'; % SET 1 (Primary - 10kg)
    '2026-05-25'; % SET 2 (Compare A - 8kg)
    '2026-05-25'; % SET 3 (Compare B - 6kg)
    '2026-06-08'; % SET 4 (RPM 10%)
    '2026-06-08'; % SET 5 (RPM 13%)
    '2026-06-08'  % SET 6 (RPM 16%)
};
% Define the Time Intervals for each test
timeLimits = {
    '17:31:30', '17:33:40'; % SET 1 (Primary - 10kg)
    '13:38:00', '13:41:00'; % SET 2 (Compare A - 8kg)
    '14:51:05', '14:55:00'; % SET 3 (Compare B - 6kg)
    '10:31:50', '10:35:30'; % SET 4 (RPM 10%)
    '10:52:00', '10:55:50'; % SET 5 (RPM 13%)
    '10:59:00', '11:00:00'  % SET 6 (RPM 16%)
};
% Define the Names for each test
datasetNames = {'10kg at 17%', '8 kg at 17%', '6 kg at 17%', 'RPM 10%', 'RPM 13%', 'RPM 16%'};
numSets = length(datasetNames);   % drives every loop below - change dataset count here only
% Global Filter & Resolution Settings
batchWindowSec = 10; 
targetLowCut   = 0.1; % Hz 
PadFactor      = 10;  % FFT Zero-Padding Multiplier
segsPerFig     = 3;   % How many segments to group per 3x3 figure
%% 1. Load the Dataset
disp('Loading dataset...');
data = readtable('sensor_data_8000.csv'); 
if ~ismember('SW420', data.Properties.VariableNames)
    data.SW420 = zeros(height(data), 1);
end
data.SW420(isnan(data.SW420)) = 0; 
data.Time = datetime(data.Time, 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
%% =========================================================================
% PART 1: FULL DEEP-DIVE PIPELINE (Loops through ALL 3 Sets)
% =========================================================================
for setIdx = 1:numSets
    currentName = datasetNames{setIdx};
    fprintf('\n======================================================\n');
    fprintf('STARTING FULL PIPELINE FOR: %s\n', currentName);
    fprintf('======================================================\n');
    
    startDT = datetime([datasetDates{setIdx} ' ' timeLimits{setIdx, 1}], 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
    endDT   = datetime([datasetDates{setIdx} ' ' timeLimits{setIdx, 2}], 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
    timeMask = (data.Time >= startDT) & (data.Time <= endDT);
    df = sortrows(data(timeMask, :), 'Time');
    if isempty(df)
        fprintf('WARNING: No data found for %s! Skipping...\n', currentName);
        continue;
    end
    
    % Crash-Proof Filtering & Smooth Timeline
    durTotal = seconds(df.Time(end) - df.Time(1));
    Fs_Global = height(df) / durTotal;
    df.SmoothTime = df.Time(1) + seconds((0:height(df)-1)' / Fs_Global);
    df.Raw_X = df.X; df.Raw_Y = df.Y; df.Raw_Z = df.Z;
    df.X = detrend(df.X); df.Y = detrend(df.Y); df.Z = detrend(df.Z);
    NyquistLimit = Fs_Global / 2;
    fprintf('Sensor Sampling Rate: %.2f Hz\n', Fs_Global);
    
    [b_main, a_main] = butter(4, targetLowCut/NyquistLimit, 'high');
    df.X = filtfilt(b_main, a_main, df.X); 
    df.Y = filtfilt(b_main, a_main, df.Y); 
    df.Z = filtfilt(b_main, a_main, df.Z);
    
    % Fixed-Time Segmentation
    elapsedTime = seconds(df.SmoothTime - df.SmoothTime(1)); 
    df.Batch_ID = floor(elapsedTime / batchWindowSec) + 1; 
    uniqueBatches = unique(df.Batch_ID);
    disp('Generating Continuous Graphs...');
    offset = setIdx * 30; 
    
    % --- GRAPH A: Full Timeline Data ---
    figure('Name', sprintf('[%s] Graph A: Full Timeline', currentName), 'Position', [50+offset, 50+offset, 1000, 800]);
    sgtitle(sprintf('[%s] Full Timeline Data', currentName), 'FontWeight', 'bold');
    ax1 = subplot(3, 1, 1);
    plot(df.SmoothTime, df.Raw_X, 'Color', [0 0.45 0.74]); hold on; plot(df.SmoothTime, df.Raw_Y, 'Color', [0.85 0.33 0.10]); plot(df.SmoothTime, df.Raw_Z, 'Color', [0.47 0.67 0.19]); hold off;
    title('Raw Acceleration'); ylabel('Amplitude'); 
    lgd = legend('X', 'Y', 'Z'); set(lgd, 'TextColor', 'w', 'Color', [0.15 0.15 0.15], 'EdgeColor', [0.3 0.3 0.3]);
    grid on; axis tight;
    ax2 = subplot(3, 1, 2);
    plot(df.SmoothTime, df.X, 'Color', [0 0.45 0.74], 'LineWidth', 1.2); hold on; plot(df.SmoothTime, df.Y, 'Color', [0.85 0.33 0.10], 'LineWidth', 1.2); plot(df.SmoothTime, df.Z, 'Color', [0.47 0.67 0.19], 'LineWidth', 1.2); hold off;
    title(sprintf('Filtered Sway (High-Pass > %.1f Hz)', targetLowCut)); ylabel('m/s^2'); grid on; axis tight;
    for i = 1:length(uniqueBatches)
        xline(df.SmoothTime(1) + seconds((i-1)*batchWindowSec), 'c--', 'LineWidth', 1.5, 'Alpha', 0.8); 
    end
    ax3 = subplot(3, 1, 3);
    plot(df.SmoothTime, df.SW420, 'Color', [0.93 0.69 0.13], 'LineWidth', 1.5);
    title('SW-420 Trigger'); ylabel('Status'); ylim([-0.1, 1.2]); yticks([0 1]); yticklabels({'OFF', 'ON'}); grid on; axis tight;
    linkaxes([ax1, ax2, ax3], 'x');
    
    % --- GRAPH B: Separated Raw Acceleration ---
    figure('Name', sprintf('[%s] Graph B: Raw', currentName), 'Position', [70+offset, 70+offset, 1000, 800]);
    sgtitle(sprintf('[%s] Raw Acceleration (Separated Axes)', currentName), 'FontWeight', 'bold');
    ax_r1 = subplot(3, 1, 1); plot(df.SmoothTime, df.Raw_X, 'Color', [0 0.45 0.74]); title('X-Axis Raw'); grid on; axis tight;
    ax_r2 = subplot(3, 1, 2); plot(df.SmoothTime, df.Raw_Y, 'Color', [0.85 0.33 0.10]); title('Y-Axis Raw'); grid on; axis tight;
    ax_r3 = subplot(3, 1, 3); plot(df.SmoothTime, df.Raw_Z, 'Color', [0.47 0.67 0.19]); title('Z-Axis Raw'); grid on; axis tight;
    linkaxes([ax_r1, ax_r2, ax_r3], 'x');
    
    % --- GRAPH C: Separated Filtered Sway ---
    figure('Name', sprintf('[%s] Graph C: Filtered', currentName), 'Position', [90+offset, 90+offset, 1000, 800]);
    sgtitle(sprintf('[%s] Filtered Structural Sway (Separated Axes)', currentName), 'FontWeight', 'bold');
    ax_f1 = subplot(3, 1, 1); plot(df.SmoothTime, df.X, 'Color', [0 0.45 0.74], 'LineWidth', 1.2); title('X-Axis Filtered'); ylabel('m/s^2'); grid on; axis tight;
    ax_f2 = subplot(3, 1, 2); plot(df.SmoothTime, df.Y, 'Color', [0.85 0.33 0.10], 'LineWidth', 1.2); title('Y-Axis Filtered'); ylabel('m/s^2'); grid on; axis tight;
    ax_f3 = subplot(3, 1, 3); plot(df.SmoothTime, df.Z, 'Color', [0.47 0.67 0.19], 'LineWidth', 1.2); title('Z-Axis Filtered'); ylabel('m/s^2'); xlabel('Time'); grid on; axis tight;
    linkaxes([ax_f1, ax_f2, ax_f3], 'x');
    for i = 1:length(uniqueBatches)
        xline(ax_f1, df.SmoothTime(1) + seconds((i-1)*batchWindowSec), 'c--', 'LineWidth', 1.5, 'Alpha', 0.8);
        xline(ax_f2, df.SmoothTime(1) + seconds((i-1)*batchWindowSec), 'c--', 'LineWidth', 1.5, 'Alpha', 0.8);
        xline(ax_f3, df.SmoothTime(1) + seconds((i-1)*batchWindowSec), 'c--', 'LineWidth', 1.5, 'Alpha', 0.8);
    end
    
    % --- GRAPH D: The Rejected Component ---
    figure('Name', sprintf('[%s] Graph D: Drift', currentName), 'Position', [110+offset, 110+offset, 1000, 800]);
    sgtitle(sprintf('[%s] The Rejected Component (< %.1f Hz Drift)', currentName, targetLowCut), 'FontWeight', 'bold');
    [b_rej, a_rej] = butter(4, targetLowCut/NyquistLimit, 'low');
    Rejected_X = filtfilt(b_rej, a_rej, df.Raw_X);
    Rejected_Y = filtfilt(b_rej, a_rej, df.Raw_Y);
    Rejected_Z = filtfilt(b_rej, a_rej, df.Raw_Z);
    ax_d1 = subplot(3, 1, 1); plot(df.SmoothTime, df.Raw_X, 'Color', [0.8 0.8 0.8], 'LineWidth', 1); hold on; plot(df.SmoothTime, Rejected_X, 'Color', [0.85 0.33 0.10], 'LineWidth', 2); hold off; title('X-Axis: Raw vs. Rejected Drift'); ylabel('Amplitude'); grid on; axis tight;
    ax_d2 = subplot(3, 1, 2); plot(df.SmoothTime, df.Raw_Y, 'Color', [0.8 0.8 0.8], 'LineWidth', 1); hold on; plot(df.SmoothTime, Rejected_Y, 'Color', [0.85 0.33 0.10], 'LineWidth', 2); hold off; title('Y-Axis: Raw vs. Rejected Drift'); ylabel('Amplitude'); grid on; axis tight;
    ax_d3 = subplot(3, 1, 3); plot(df.SmoothTime, df.Raw_Z, 'Color', [0.8 0.8 0.8], 'LineWidth', 1); hold on; plot(df.SmoothTime, Rejected_Z, 'Color', [0.85 0.33 0.10], 'LineWidth', 2); hold off; title('Z-Axis: Raw vs. Rejected Drift'); ylabel('Amplitude'); xlabel('Time'); grid on; axis tight;
    linkaxes([ax_d1, ax_d2, ax_d3], 'x');
    
    % --- GRAPH E: High-Resolution Frequency Spectra (Per Segmentation, 3x3 Grid) ---
    disp('Computing Individual Segment FFTs...');
    L_batch = floor(batchWindowSec * Fs_Global); 
    NFFT = L_batch * PadFactor; 
    f = Fs_Global * (0:(floor(NFFT/2))) / NFFT; 
    numSegments = length(uniqueBatches);
    numFigGroups = ceil(numSegments / segsPerFig);
    
    for figGroup = 1:numFigGroups
        groupStart = (figGroup - 1) * segsPerFig + 1;
        groupEnd   = min(figGroup * segsPerFig, numSegments);
        segsInGroup = groupStart:groupEnd;
        
        figPos = [130 + offset + (figGroup*10), 130 + offset + (figGroup*10), 1400, 900];
        figure('Name', sprintf('[%s] Segs %d-%d', currentName, groupStart, groupEnd), 'Position', figPos);
        sgtitle(sprintf('[%s] High-Res Normalized FFT: Segments %d to %d', currentName, groupStart, groupEnd), 'FontWeight', 'bold', 'FontSize', 14);
        
        axGroup = [];
        for col = 1:length(segsInGroup)
            i = segsInGroup(col);
            bID = uniqueBatches(i);
            bData = df(df.Batch_ID == bID, :);
            segStart = bData.Time(1);
            segEnd   = bData.Time(end);
            timeStr  = sprintf('%s-%s', string(segStart, 'HH:mm:ss'), string(segEnd, 'HH:mm:ss'));
            
            if height(bData) < L_batch; continue; end
            bData = bData(1:L_batch, :); 
            
            % Peak Amplitude Normalization
            bData.X = bData.X / max(abs(bData.X));
            bData.Y = bData.Y / max(abs(bData.Y));
            bData.Z = bData.Z / max(abs(bData.Z));
            
            fft_X = fft(bData.X, NFFT); P2_X = abs(fft_X / L_batch); P1_X = P2_X(1:floor(NFFT/2)+1); P1_X(2:end-1) = 2 * P1_X(2:end-1);
            fft_Y = fft(bData.Y, NFFT); P2_Y = abs(fft_Y / L_batch); P1_Y = P2_Y(1:floor(NFFT/2)+1); P1_Y(2:end-1) = 2 * P1_Y(2:end-1);
            fft_Z = fft(bData.Z, NFFT); P2_Z = abs(fft_Z / L_batch); P1_Z = P2_Z(1:floor(NFFT/2)+1); P1_Z(2:end-1) = 2 * P1_Z(2:end-1);
            
            limitIdx = find(f <= 15, 1, 'last'); 
            [maxX, idxX] = max(P1_X(1:limitIdx)); freqX = f(idxX);
            [maxY, idxY] = max(P1_Y(1:limitIdx)); freqY = f(idxY);
            [maxZ, idxZ] = max(P1_Z(1:limitIdx)); freqZ = f(idxZ);
            
            % Row 1 = X-Axis
            axX = subplot(3, 3, col);
            plot(f, P1_X, 'Color', [0 0.45 0.74], 'LineWidth', 1.5); hold on; plot(freqX, maxX, 'rv', 'MarkerFaceColor', 'r', 'MarkerSize', 6); text(freqX + 0.2, maxX, sprintf('%.2f Hz', freqX), 'Color', 'r', 'FontWeight', 'bold'); hold off;
            title(sprintf('Seg %d (%s)\nX-Axis', i, timeStr)); ylabel('Norm. Amplitude'); grid on; axis tight; xlim([0, 15]); ylim([0, max(maxX*1.2, 0.1)]);
            axGroup = [axGroup, axX];
            
            % Row 2 = Y-Axis
            axY = subplot(3, 3, col + 3);
            plot(f, P1_Y, 'Color', [0.85 0.33 0.10], 'LineWidth', 1.5); hold on; plot(freqY, maxY, 'rv', 'MarkerFaceColor', 'r', 'MarkerSize', 6); text(freqY + 0.2, maxY, sprintf('%.2f Hz', freqY), 'Color', 'r', 'FontWeight', 'bold'); hold off;
            title('Y-Axis'); ylabel('Norm. Amplitude'); grid on; axis tight; xlim([0, 15]); ylim([0, max(maxY*1.2, 0.1)]);
            axGroup = [axGroup, axY];
            
            % Row 3 = Z-Axis
            axZ = subplot(3, 3, col + 6);
            plot(f, P1_Z, 'Color', [0.47 0.67 0.19], 'LineWidth', 1.5); hold on; plot(freqZ, maxZ, 'rv', 'MarkerFaceColor', 'r', 'MarkerSize', 6); text(freqZ + 0.2, maxZ, sprintf('%.2f Hz', freqZ), 'Color', 'r', 'FontWeight', 'bold'); hold off;
            title('Z-Axis'); xlabel('Frequency (Hz)'); ylabel('Norm. Amplitude'); grid on; axis tight; xlim([0, 15]); ylim([0, max(maxZ*1.2, 0.1)]);
            axGroup = [axGroup, axZ];
        end
        if ~isempty(axGroup); linkaxes(axGroup, 'x'); end
    end
end
%% =========================================================================
% PART 2: HIGH-RES COMPARISON (GENERAL 3x3 + INDIVIDUAL CLEAR VISUALS)
% =========================================================================
fprintf('\n======================================================\n');
disp('Initiating Overall Analysis & One-by-One Generation...');
fprintf('======================================================\n');

% 1. Create the GENERAL overview figure first
fig_general = figure('Name', 'GENERAL: FFT 3x3 Overall Comparison', 'Position', [20, 20, 1600, 900]);
sgtitle('GENERAL VIEW: High-Resolution Normalized FFT Comparison', 'FontWeight', 'bold', 'FontSize', 16);

globalPeaksX = zeros(numSets,1); 

for k = 1:numSets
    dt_Start = datetime([datasetDates{k} ' ' timeLimits{k,1}], 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
    dt_End   = datetime([datasetDates{k} ' ' timeLimits{k,2}], 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
    mask = (data.Time >= dt_Start) & (data.Time <= dt_End);
    df_comp = sortrows(data(mask, :), 'Time');
    
    if isempty(df_comp); continue; end
    
    dur = seconds(df_comp.Time(end) - df_comp.Time(1));
    Fs_comp = height(df_comp) / dur;
    df_comp.X = detrend(df_comp.X); df_comp.Y = detrend(df_comp.Y); df_comp.Z = detrend(df_comp.Z);
    [b_c, a_c] = butter(4, targetLowCut/(Fs_comp/2), 'high');
    df_comp.X = filtfilt(b_c, a_c, df_comp.X); 
    df_comp.Y = filtfilt(b_c, a_c, df_comp.Y); 
    df_comp.Z = filtfilt(b_c, a_c, df_comp.Z);
    
    df_comp.X = df_comp.X / max(abs(df_comp.X));
    df_comp.Y = df_comp.Y / max(abs(df_comp.Y));
    df_comp.Z = df_comp.Z / max(abs(df_comp.Z));
    
    L_c = height(df_comp);
    NFFT_c = L_c * PadFactor; 
    f_c = Fs_comp * (0:(floor(NFFT_c/2))) / NFFT_c;
    
    fft_X = fft(df_comp.X, NFFT_c); P2_X = abs(fft_X / L_c); P1_X = P2_X(1:floor(NFFT_c/2)+1); P1_X(2:end-1) = 2 * P1_X(2:end-1);
    fft_Y = fft(df_comp.Y, NFFT_c); P2_Y = abs(fft_Y / L_c); P1_Y = P2_Y(1:floor(NFFT_c/2)+1); P1_Y(2:end-1) = 2 * P1_Y(2:end-1);
    fft_Z = fft(df_comp.Z, NFFT_c); P2_Z = abs(fft_Z / L_c); P1_Z = P2_Z(1:floor(NFFT_c/2)+1); P1_Z(2:end-1) = 2 * P1_Z(2:end-1);
    
    limIdx = find(f_c <= 15, 1, 'last');
    [maxX, idxX] = max(P1_X(1:limIdx)); freqX = f_c(idxX); globalPeaksX(k) = freqX;
    [maxY, idxY] = max(P1_Y(1:limIdx)); freqY = f_c(idxY);
    [maxZ, idxZ] = max(P1_Z(1:limIdx)); freqZ = f_c(idxZ);
    
    % --- DAMPING RATIO ESTIMATION (Half-Power Bandwidth for X-Axis) ---
    halfPowerAmp = maxX / sqrt(2);
    searchRange = max(1, idxX-800) : min(length(P1_X), idxX+800); 
    aboveThresh = P1_X(searchRange) >= halfPowerAmp;
    
    if any(aboveThresh)
        firstAbove = find(aboveThresh, 1, 'first');
        lastAbove  = find(aboveThresh, 1, 'last');
        f1 = f_c(searchRange(firstAbove));
        f2 = f_c(searchRange(lastAbove));
        damping_ratio_X = (f2 - f1) / (2 * freqX);
        fprintf('[%s] X-Axis Damping Ratio: %.4f (Peak at %.2f Hz)\n', datasetNames{k}, damping_ratio_X, freqX);
    else
        fprintf('[%s] X-Axis Damping Ratio: Could not calculate (peak too noisy).\n', datasetNames{k});
    end
    
    % ============================================================
    % PLOT 1: Add to the GENERAL 3x3 Figure
    % ============================================================
    figure(fig_general); % Command MATLAB to focus on the 3x3 general figure
    
    subplot(3, numSets, k);
    plot(f_c, P1_X, 'Color', [0 0.45 0.74], 'LineWidth', 1.5); hold on; plot(freqX, maxX, 'rv', 'MarkerFaceColor', 'r'); 
    text(freqX + 0.2, maxX, sprintf('%.2f Hz', freqX), 'Color', 'r', 'FontWeight', 'bold'); hold off;
    title(sprintf('%s\nX-Axis', datasetNames{k})); ylabel('Norm. Amplitude'); grid on; xlim([0, 15]); ylim([0, max(maxX*1.2, 0.1)]);
    
    subplot(3, numSets, k+numSets);
    plot(f_c, P1_Y, 'Color', [0.85 0.33 0.10], 'LineWidth', 1.5); hold on; plot(freqY, maxY, 'rv', 'MarkerFaceColor', 'r');
    text(freqY + 0.2, maxY, sprintf('%.2f Hz', freqY), 'Color', 'r', 'FontWeight', 'bold'); hold off;
    title('Y-Axis'); ylabel('Norm. Amplitude'); grid on; xlim([0, 15]); ylim([0, max(maxY*1.2, 0.1)]);
    
    subplot(3, numSets, k+2*numSets);
    plot(f_c, P1_Z, 'Color', [0.47 0.67 0.19], 'LineWidth', 1.5); hold on; plot(freqZ, maxZ, 'rv', 'MarkerFaceColor', 'r');
    text(freqZ + 0.2, maxZ, sprintf('%.2f Hz', freqZ), 'Color', 'r', 'FontWeight', 'bold'); hold off;
    title('Z-Axis'); xlabel('Frequency (Hz)'); ylabel('Norm. Amplitude'); grid on; xlim([0, 15]); ylim([0, max(maxZ*1.2, 0.1)]);

    % ============================================================
    % PLOT 2: Generate the ONE-BY-ONE Detailed Figure
    % ============================================================
    fig_indiv = figure('Name', sprintf('Detailed FFT - %s', datasetNames{k}), 'Position', [100+(k*30), 100+(k*30), 1000, 800]);
    sgtitle(sprintf('CLEAR VISUAL: %s Payload', datasetNames{k}), 'FontWeight', 'bold', 'FontSize', 18);
    
    % Define a tighter frequency window to see the low-frequency structural peaks clearly
    zoomFreq = 8; 
    
    ax_ix = subplot(3, 1, 1);
    plot(f_c, P1_X, 'Color', [0 0.45 0.74], 'LineWidth', 2); hold on; plot(freqX, maxX, 'rv', 'MarkerFaceColor', 'r', 'MarkerSize', 8); 
    text(freqX + 0.1, maxX, sprintf('%.2f Hz', freqX), 'Color', 'r', 'FontWeight', 'bold', 'FontSize', 12); hold off;
    title('X-Axis Spectrum (Detailed)', 'FontSize', 14); ylabel('Norm. Amp'); grid on; 
    xlim([0, zoomFreq]); ylim([0, maxX*1.3]); % <-- Dynamically scales to 130% of the peak
    
    ax_iy = subplot(3, 1, 2);
    plot(f_c, P1_Y, 'Color', [0.85 0.33 0.10], 'LineWidth', 2); hold on; plot(freqY, maxY, 'rv', 'MarkerFaceColor', 'r', 'MarkerSize', 8);
    text(freqY + 0.1, maxY, sprintf('%.2f Hz', freqY), 'Color', 'r', 'FontWeight', 'bold', 'FontSize', 12); hold off;
    title('Y-Axis Spectrum (Detailed)', 'FontSize', 14); ylabel('Norm. Amp'); grid on; 
    xlim([0, zoomFreq]); ylim([0, maxY*1.3]); 
    
    ax_iz = subplot(3, 1, 3);
    plot(f_c, P1_Z, 'Color', [0.47 0.67 0.19], 'LineWidth', 2); hold on; plot(freqZ, maxZ, 'rv', 'MarkerFaceColor', 'r', 'MarkerSize', 8);
    text(freqZ + 0.1, maxZ, sprintf('%.2f Hz', freqZ), 'Color', 'r', 'FontWeight', 'bold', 'FontSize', 12); hold off;
    title('Z-Axis Spectrum (Detailed)', 'FontSize', 14); xlabel('Frequency (Hz)', 'FontSize', 12); ylabel('Norm. Amp'); grid on; 
    xlim([0, zoomFreq]); ylim([0, maxZ*1.3]); 
    
    % Link the X-axes on the clear visual so zooming in pans across all 3 axes simultaneously
    linkaxes([ax_ix, ax_iy, ax_iz], 'x');
end
%% =========================================================================
% PART 3: SEGMENT-BY-SEGMENT COMPARISON GRID (Side-by-Side)
% =========================================================================
fprintf('\n======================================================\n');
disp('Initiating Segment-by-Segment Side-by-Side Comparison...');
fprintf('======================================================\n');
maxCompareSegs = 6; % Compare the first 6 segments (60 seconds total)
for segIdx = 1:maxCompareSegs
    figure('Name', sprintf('Segment %d Comparison', segIdx), 'Position', [40+(segIdx*20), 40+(segIdx*20), 1600, 900]);
    sgtitle(sprintf('Segment %d Comparison (Seconds %d to %d)\nPayload Effect on Resonant Frequency', segIdx, (segIdx-1)*batchWindowSec, segIdx*batchWindowSec), 'FontWeight', 'bold', 'FontSize', 16);
    
    for k = 1:numSets
        dt_Start = datetime([datasetDates{k} ' ' timeLimits{k,1}], 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
        dt_End   = datetime([datasetDates{k} ' ' timeLimits{k,2}], 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
        mask = (data.Time >= dt_Start) & (data.Time <= dt_End);
        df_comp = sortrows(data(mask, :), 'Time');
        
        if isempty(df_comp)
            continue;
        end
        
        dur = seconds(df_comp.Time(end) - df_comp.Time(1));
        Fs_comp = height(df_comp) / dur;
        df_comp.SmoothTime = df_comp.Time(1) + seconds((0:height(df_comp)-1)' / Fs_comp);
        
        df_comp.X = detrend(df_comp.X); df_comp.Y = detrend(df_comp.Y); df_comp.Z = detrend(df_comp.Z);
        [b_c, a_c] = butter(4, targetLowCut/(Fs_comp/2), 'high');
        df_comp.X = filtfilt(b_c, a_c, df_comp.X); 
        df_comp.Y = filtfilt(b_c, a_c, df_comp.Y); 
        df_comp.Z = filtfilt(b_c, a_c, df_comp.Z);
        
        elapsedTime = seconds(df_comp.SmoothTime - df_comp.SmoothTime(1)); 
        df_comp.Batch_ID = floor(elapsedTime / batchWindowSec) + 1; 
        
        bData = df_comp(df_comp.Batch_ID == segIdx, :);
        L_c = height(bData);
        
        if L_c < (batchWindowSec * Fs_comp * 0.9) 
            continue;
        end
        
        bData.X = bData.X / max(abs(bData.X));
        bData.Y = bData.Y / max(abs(bData.Y));
        bData.Z = bData.Z / max(abs(bData.Z));
        
        NFFT_c = L_c * PadFactor; 
        f_c = Fs_comp * (0:(floor(NFFT_c/2))) / NFFT_c;
        
        fft_X = fft(bData.X, NFFT_c); P2_X = abs(fft_X / L_c); P1_X = P2_X(1:floor(NFFT_c/2)+1); P1_X(2:end-1) = 2 * P1_X(2:end-1);
        fft_Y = fft(bData.Y, NFFT_c); P2_Y = abs(fft_Y / L_c); P1_Y = P2_Y(1:floor(NFFT_c/2)+1); P1_Y(2:end-1) = 2 * P1_Y(2:end-1);
        fft_Z = fft(bData.Z, NFFT_c); P2_Z = abs(fft_Z / L_c); P1_Z = P2_Z(1:floor(NFFT_c/2)+1); P1_Z(2:end-1) = 2 * P1_Z(2:end-1);
        
        limIdx = find(f_c <= 15, 1, 'last');
        [maxX, idxX] = max(P1_X(1:limIdx)); freqX = f_c(idxX);
        [maxY, idxY] = max(P1_Y(1:limIdx)); freqY = f_c(idxY);
        [maxZ, idxZ] = max(P1_Z(1:limIdx)); freqZ = f_c(idxZ);
        
        subplot(3, numSets, k);
        plot(f_c, P1_X, 'Color', [0 0.45 0.74], 'LineWidth', 1.5); hold on; plot(freqX, maxX, 'rv', 'MarkerFaceColor', 'r'); 
        text(freqX + 0.2, maxX, sprintf('%.2f Hz', freqX), 'Color', 'r', 'FontWeight', 'bold'); hold off;
        title(sprintf('%s\nX-Axis', datasetNames{k})); ylabel('Norm. Amplitude'); grid on; xlim([0, 15]); ylim([0, max(maxX*1.2, 0.1)]);
        
        subplot(3, numSets, k+numSets);
        plot(f_c, P1_Y, 'Color', [0.85 0.33 0.10], 'LineWidth', 1.5); hold on; plot(freqY, maxY, 'rv', 'MarkerFaceColor', 'r');
        text(freqY + 0.2, maxY, sprintf('%.2f Hz', freqY), 'Color', 'r', 'FontWeight', 'bold'); hold off;
        title('Y-Axis'); ylabel('Norm. Amplitude'); grid on; xlim([0, 15]); ylim([0, max(maxY*1.2, 0.1)]);
        
        subplot(3, numSets, k+2*numSets);
        plot(f_c, P1_Z, 'Color', [0.47 0.67 0.19], 'LineWidth', 1.5); hold on; plot(freqZ, maxZ, 'rv', 'MarkerFaceColor', 'r');
        text(freqZ + 0.2, maxZ, sprintf('%.2f Hz', freqZ), 'Color', 'r', 'FontWeight', 'bold'); hold off;
        title('Z-Axis'); xlabel('Frequency (Hz)'); ylabel('Norm. Amplitude'); grid on; xlim([0, 15]); ylim([0, max(maxZ*1.2, 0.1)]);
    end
end
%% =========================================================================
% PART 4: EDUCATIONAL VISUALIZATION: Normal vs. High-Resolution FFT
% =========================================================================
fprintf('\n======================================================\n');
disp('Generating Normal vs. High-Res FFT Demonstration...');
fprintf('======================================================\n');
dt_Start = datetime([datasetDates{1} ' ' timeLimits{1,1}], 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
dt_End   = dt_Start + seconds(10);
mask = (data.Time >= dt_Start) & (data.Time <= dt_End);
df_demo = sortrows(data(mask, :), 'Time');
if ~isempty(df_demo)
    dur = seconds(df_demo.Time(end) - df_demo.Time(1));
    Fs_demo = height(df_demo) / dur;
    df_demo.X = detrend(df_demo.X);
    [b_d, a_d] = butter(4, targetLowCut/(Fs_demo/2), 'high');
    X_filt = filtfilt(b_d, a_d, df_demo.X);
    X_filt = X_filt / max(abs(X_filt));
    
    L_d = length(X_filt);
    PadFactor_demo = 10;
    NFFT_d = L_d * PadFactor_demo;
    
    f_norm = Fs_demo * (0:(floor(L_d/2))) / L_d;
    fft_norm = fft(X_filt);
    P2_norm = abs(fft_norm / L_d);
    P1_norm = P2_norm(1:floor(L_d/2)+1);
    P1_norm(2:end-1) = 2 * P1_norm(2:end-1);
    
    f_high = Fs_demo * (0:(floor(NFFT_d/2))) / NFFT_d;
    fft_high = fft(X_filt, NFFT_d);
    P2_high = abs(fft_high / L_d); 
    P1_high = P2_high(1:floor(NFFT_d/2)+1);
    P1_high(2:end-1) = 2 * P1_high(2:end-1);
    
    figure('Name', 'FFT Resolution Comparison', 'Position', [100, 100, 1200, 500]);
    sgtitle('The Effect of Zero-Padding: Normal vs. High-Resolution Normalized FFT', 'FontWeight', 'bold', 'FontSize', 16);
    
    subplot(1, 2, 1);
    plot(f_norm, P1_norm, 'ko-', 'LineWidth', 1, 'MarkerSize', 4, 'MarkerFaceColor', 'k'); hold on;
    plot(f_high, P1_high, 'Color', [0 0.45 0.74], 'LineWidth', 2); hold off;
    title('Wide View (0 - 10 Hz)');
    xlabel('Frequency (Hz)'); ylabel('Norm. Amplitude');
    legend('Normal Resolution (Raw Bins)', 'High Resolution (Zero-Padded)', 'Location', 'northeast');
    xlim([0, 10]); grid on;
    
    subplot(1, 2, 2);
    plot(f_norm, P1_norm, 'ko-', 'LineWidth', 1.5, 'MarkerSize', 6, 'MarkerFaceColor', 'k'); hold on;
    plot(f_high, P1_high, 'Color', [0 0.45 0.74], 'LineWidth', 2); hold off;
    
    [maxVal, maxIdx] = max(P1_high(f_high <= 2)); 
    plot(f_high(maxIdx), maxVal, 'rv', 'MarkerFaceColor', 'r', 'MarkerSize', 8);
    
    title('Zoomed View (Peak Interpolation)');
    xlabel('Frequency (Hz)'); ylabel('Norm. Amplitude');
    xlim([0, 1.5]); ylim([0, maxVal*1.2]); 
    grid on;
end
%% =========================================================================
% PART 5: OVERALL 3x3 COMPARATIVE ANALYSIS (Normal Resolution / No Padding)
% =========================================================================
fprintf('\n======================================================\n');
disp('Generating Normal Resolution 3x3 Comparison Grid...');
fprintf('======================================================\n');
figure('Name', 'FFT 3x3 Normal Resolution', 'Position', [40, 40, 1600, 900]);
sgtitle('Normal Resolution Normalized FFT Comparison: Raw Frequency Bins (No Zero-Padding)', 'FontWeight', 'bold', 'FontSize', 16);
for k = 1:numSets
    dt_Start = datetime([datasetDates{k} ' ' timeLimits{k,1}], 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
    dt_End   = datetime([datasetDates{k} ' ' timeLimits{k,2}], 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
    mask = (data.Time >= dt_Start) & (data.Time <= dt_End);
    df_comp = sortrows(data(mask, :), 'Time');
    
    if isempty(df_comp); continue; end
    
    dur = seconds(df_comp.Time(end) - df_comp.Time(1));
    Fs_comp = height(df_comp) / dur;
    
    df_comp.X = detrend(df_comp.X); df_comp.Y = detrend(df_comp.Y); df_comp.Z = detrend(df_comp.Z);
    [b_c, a_c] = butter(4, targetLowCut/(Fs_comp/2), 'high');
    df_comp.X = filtfilt(b_c, a_c, df_comp.X); 
    df_comp.Y = filtfilt(b_c, a_c, df_comp.Y); 
    df_comp.Z = filtfilt(b_c, a_c, df_comp.Z);
    
    df_comp.X = df_comp.X / max(abs(df_comp.X));
    df_comp.Y = df_comp.Y / max(abs(df_comp.Y));
    df_comp.Z = df_comp.Z / max(abs(df_comp.Z));
    
    L_c = height(df_comp);
    f_norm = Fs_comp * (0:(floor(L_c/2))) / L_c; 
    
    fft_X = fft(df_comp.X); P2_X = abs(fft_X / L_c); P1_X = P2_X(1:floor(L_c/2)+1); P1_X(2:end-1) = 2 * P1_X(2:end-1);
    fft_Y = fft(df_comp.Y); P2_Y = abs(fft_Y / L_c); P1_Y = P2_Y(1:floor(L_c/2)+1); P1_Y(2:end-1) = 2 * P1_Y(2:end-1);
    fft_Z = fft(df_comp.Z); P2_Z = abs(fft_Z / L_c); P1_Z = P2_Z(1:floor(L_c/2)+1); P1_Z(2:end-1) = 2 * P1_Z(2:end-1);
    
    limIdx = find(f_norm <= 15, 1, 'last');
    [maxX, idxX] = max(P1_X(1:limIdx)); freqX = f_norm(idxX);
    [maxY, idxY] = max(P1_Y(1:limIdx)); freqY = f_norm(idxY);
    [maxZ, idxZ] = max(P1_Z(1:limIdx)); freqZ = f_norm(idxZ);
    
    subplot(3, numSets, k);
    plot(f_norm, P1_X, 'Color', [0 0.45 0.74], 'LineWidth', 1.2); hold on; 
    plot(freqX, maxX, 'rv', 'MarkerFaceColor', 'r'); 
    text(freqX + 0.2, maxX, sprintf('%.2f Hz', freqX), 'Color', 'r', 'FontWeight', 'bold'); hold off;
    title(sprintf('%s\nX-Axis', datasetNames{k})); ylabel('Norm. Amplitude'); grid on; xlim([0, 15]); ylim([0, max(maxX*1.2, 0.1)]);
    
    subplot(3, numSets, k+numSets);
    plot(f_norm, P1_Y, 'Color', [0.85 0.33 0.10], 'LineWidth', 1.2); hold on; 
    plot(freqY, maxY, 'rv', 'MarkerFaceColor', 'r');
    text(freqY + 0.2, maxY, sprintf('%.2f Hz', freqY), 'Color', 'r', 'FontWeight', 'bold'); hold off;
    title('Y-Axis'); ylabel('Norm. Amplitude'); grid on; xlim([0, 15]); ylim([0, max(maxY*1.2, 0.1)]);
    
    subplot(3, numSets, k+2*numSets);
    plot(f_norm, P1_Z, 'Color', [0.47 0.67 0.19], 'LineWidth', 1.2); hold on; 
    plot(freqZ, maxZ, 'rv', 'MarkerFaceColor', 'r');
    text(freqZ + 0.2, maxZ, sprintf('%.2f Hz', freqZ), 'Color', 'r', 'FontWeight', 'bold'); hold off;
    title('Z-Axis'); xlabel('Frequency (Hz)'); ylabel('Norm. Amplitude'); grid on; xlim([0, 15]); ylim([0, max(maxZ*1.2, 0.1)]);
end
%% =========================================================================
% PART 6A: X-AXIS MULTI-RESOLUTION SEGMENTATION & STA/LTA (HILBERT) + SMS
% =========================================================================
for setIdx = 1:numSets
    currentName = datasetNames{setIdx};
    fprintf('\nGenerating X-Axis STA/LTA Multi-Resolution Analysis for: %s\n', currentName);
    
    startDT = datetime([datasetDates{setIdx} ' ' timeLimits{setIdx, 1}], 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
    endDT   = datetime([datasetDates{setIdx} ' ' timeLimits{setIdx, 2}], 'InputFormat', 'yyyy-MM-dd HH:mm:ss');
    mask = (data.Time >= startDT) & (data.Time <= endDT);
    df_stft = sortrows(data(mask, :), 'Time');
    
    if ~isempty(df_stft)
        dur = seconds(df_stft.Time(end) - df_stft.Time(1));
        Fs_stft = height(df_stft) / dur;
        df_stft.SmoothTime = df_stft.Time(1) + seconds((0:height(df_stft)-1)' / Fs_stft);
        
        [b_s, a_s] = butter(4, targetLowCut/(Fs_stft/2), 'high');
        X_stft = filtfilt(b_s, a_s, detrend(df_stft.X));
        X_stft = X_stft / max(abs(X_stft)); % Normalize
        
        figOffset = setIdx * 30;
        windowLength = 256; 
        overlap = round(windowLength * 0.90); 
        nfft = windowLength * PadFactor; 
        
        % 6A(1). BUILT-IN SPECTROGRAM (STFT)
        figure('Name', sprintf('STFT Spectrogram (X-Axis) - %s', currentName), 'Position', [100+figOffset, 100+figOffset, 1000, 500]);
        spectrogram(X_stft, windowLength, overlap, nfft, Fs_stft, 'yaxis');
        ylim([0 3]); caxis('auto'); colormap turbo; 
        title(sprintf('STFT Spectrogram (Normalized X-Axis, 256-Window): %s', currentName), 'FontWeight', 'bold', 'FontSize', 14);
        xlabel('Time (Minutes)', 'FontWeight', 'bold'); ylabel('Frequency (Hz)', 'FontWeight', 'bold');
        
        % 6A(2). MANUAL FFT SEGMENTATION
        stepSize = windowLength - overlap;
        numSegments = floor((length(X_stft) - windowLength) / stepSize);
        windowFunc = hamming(windowLength); 
        
        stftMatrix = zeros(floor(windowLength/2) + 1, numSegments);
        for seg = 1:numSegments
            idx = (seg-1)*stepSize + 1;
            segment = X_stft(idx : idx + windowLength - 1);
            windowedSegment = segment .* windowFunc; 
            fftResult = fft(windowedSegment, windowLength);
            stftMatrix(:, seg) = abs(fftResult(1 : floor(windowLength/2) + 1));
        end
        
        figure('Name', sprintf('Manual FFT Seg (X-Axis) - %s', currentName), 'Position', [120+figOffset, 120+figOffset, 1000, 500]);
        imagesc(stftMatrix);
        axis xy; colormap turbo;
        title(sprintf('Manual FFT Segmentation Proof (Normalized X-Axis): %s', currentName), 'FontWeight', 'bold', 'FontSize', 14);
        xlabel('Segment Number', 'FontWeight', 'bold'); ylabel('Freq Bin', 'FontWeight', 'bold');
        
        % ===============================================================
        % 6A(4). STA/LTA MULTI-EVENT DETECTION (DYNAMIC CALIBRATION) + SMS + BUZZER
        % ===============================================================
        T_onset = 0.5;   % Theoretical rise time of vibration (seconds)
        k_smooth = 5;    % Smoothing multiplier for LTA window
        
        sta_samples = round(T_onset * Fs_stft);
        lta_samples = round(k_smooth * sta_samples); 
        % NOTE: fixed-seconds min_separation (previously 40.0s, then
        % 10.0s) is gone. Event separation is now handled adaptively by
        % detectTriggerEvents() below via a trigger/de-trigger state
        % machine, so no separation-in-seconds parameter is needed here.
        
        % Hilbert Transform for smooth professional envelope
        analytic_signal = hilbert(X_stft);
        signal_envelope = abs(analytic_signal);
        
        STA = movmean(signal_envelope, [sta_samples 0]); 
        LTA = movmean(signal_envelope, [lta_samples 0]);
        STA_LTA_Ratio = STA ./ LTA; 
        
        % ---------------------------------------------------------------
        % --- NEW CODE: VISUALIZE THE HIDDEN ENVELOPE (SEPARATED) ---
        % ---------------------------------------------------------------
        figure('Name', sprintf('Hilbert Envelope - %s', currentName), 'Position', [200+figOffset, 200+figOffset, 1200, 600]);
        
        % Top Graph: The Raw Signal (Swinging positive and negative)
        ax_raw = subplot(2, 1, 1);
        plot(df_stft.SmoothTime, X_stft, 'Color', [0 0.45 0.74], 'LineWidth', 1);
        title(sprintf('Raw Oscillating Signal (X_{stft}): %s', currentName), 'FontWeight', 'bold', 'FontSize', 14);
        ylabel('Norm. Amplitude'); grid on; axis tight;
        
        % Bottom Graph: The Extracted Envelope (Pure positive energy)
        ax_env = subplot(2, 1, 2);
        plot(df_stft.SmoothTime, signal_envelope, 'Color', [0.85 0.33 0.10], 'LineWidth', 1.5);
        title('Extracted Hilbert Envelope (signal\_envelope)', 'FontWeight', 'bold', 'FontSize', 14);
        ylabel('Power [0-1]'); xlabel('Time'); grid on; axis tight;
        
        % Link the X-axes so zooming on one zooms on the other perfectly
        linkaxes([ax_raw, ax_env], 'x');
        % ---------------------------------------------------------------
        % --- DYNAMIC THRESHOLD CALIBRATION (STA/LTA) ---
        % ADAPTIVE calib window: 15% of this dataset's total duration,
        % clamped to [10s, 30s]. A fixed 30s was tuned against the 10kg
        % run (130s window, motor starts ~31s) but silently ate HALF of
        % the 60s RPM16% run (SET 6), calibrating the "quiet" baseline on
        % data that likely already includes motor noise. dur is the total
        % duration of this dataset's window, already computed above via
        % Fs_stft = height(df_stft) / dur.
        calib_sec = min(max(0.15 * dur, 10), 30);
        calib_idx = find(seconds(df_stft.SmoothTime - df_stft.SmoothTime(1)) <= calib_sec, 1, 'last');
        if isempty(calib_idx), calib_idx = length(STA_LTA_Ratio); end
        
        % 1. Calculate Steady-State Baseline 
        Steady_State_Baseline = prctile(STA_LTA_Ratio(1:calib_idx), 99); 
        
        % 2. Define Deviation Tolerance 
        Deviation_Tolerance = 1.40;    % 40% operational margin
        
        % 3. Calculate Final Critical Threshold
        Critical_Threshold = Steady_State_Baseline * Deviation_Tolerance; 
        
        [pks, locs] = detectTriggerEvents(STA_LTA_Ratio, Critical_Threshold, Steady_State_Baseline);
        
        figure('Name', sprintf('STA/LTA (X-Axis) - %s', currentName), 'Position', [160+figOffset, 160+figOffset, 1200, 800]);
        sgtitle(sprintf('STA/LTA Collapse Detection (Normalized X-Axis Hilbert): %s', currentName), 'FontWeight', 'bold', 'FontSize', 16);
        
        ax_top = subplot(2, 1, 1);
        plot(df_stft.SmoothTime, X_stft, 'Color', [0 0.45 0.74], 'LineWidth', 1.2);
        title('Normalized Filtered Structural Sway (X-Axis)'); ylabel('Norm. Amp [0-1]'); grid on; axis tight;
        
        ax_bot = subplot(2, 1, 2);
        plot(df_stft.SmoothTime, STA_LTA_Ratio, 'Color', [0.85 0.33 0.10], 'LineWidth', 1.5); hold on;
        yline(Critical_Threshold, 'r--', sprintf('Critical Threshold (%.2f = %.2f Baseline x %.2f Tolerance)', Critical_Threshold, Steady_State_Baseline, Deviation_Tolerance), 'LineWidth', 2, 'LabelHorizontalAlignment', 'left');
        title('STA/LTA Ratio (Empirically Calibrated Baseline)'); ylabel('Ratio'); xlabel('Time'); grid on; axis tight;
        
        currentYLim = ylim; ylim([min(currentYLim(1), 0), max(currentYLim(2), Critical_Threshold * 1.4)]);
        
        if ~isempty(locs)
            for i = 1:length(locs)
                event_idx = locs(i);
                event_time = df_stft.SmoothTime(event_idx);
                elapsed_sec = seconds(event_time - df_stft.SmoothTime(1));
                
                % Find peak sway value near this trigger
                window_samples_loc = round(1.0 * Fs_stft);
                search_idx = max(1, event_idx - window_samples_loc) : min(length(X_stft), event_idx + window_samples_loc);
                [peak_sway_val, rel_peak_idx] = max(abs(X_stft(search_idx)));
                peak_time = df_stft.SmoothTime(search_idx(rel_peak_idx));
                
                % Calculate frequency for the event
                local_data = X_stft(search_idx);
                if length(local_data) > (0.5 * Fs_stft) 
                    NFFT_loc = length(local_data) * PadFactor;
                    f_loc = Fs_stft * (0:(floor(NFFT_loc/2))) / NFFT_loc;
                    fft_loc = fft(local_data, NFFT_loc);
                    P1_loc = abs(fft_loc / length(local_data));
                    P1_loc = P1_loc(1:floor(NFFT_loc/2)+1);
                    valid_f_idx = find(f_loc <= 15);
                    [~, max_idx_loc_freq] = max(P1_loc(valid_f_idx));
                    event_freq = f_loc(valid_f_idx(max_idx_loc_freq));
                else
                    event_freq = 0;
                end
                
                % --- MAPPING EVERY POINT TO AXES (TOP GRAPH) ---
                hold(ax_top, 'on');
                plot(ax_top, [df_stft.SmoothTime(1), peak_time], [peak_sway_val, peak_sway_val], 'r:', 'LineWidth', 1.2);
                plot(ax_top, [peak_time, peak_time], [0, peak_sway_val], 'r:', 'LineWidth', 1.2);
                plot(ax_top, peak_time, peak_sway_val, 'ro', 'MarkerFaceColor', 'r', 'MarkerSize', 5);
                text(ax_top, df_stft.SmoothTime(1), peak_sway_val, sprintf('  %.2f', peak_sway_val), 'Color', 'r', 'VerticalAlignment', 'bottom', 'FontWeight', 'bold', 'FontSize', 8);
                xline(ax_top, event_time, 'r-', 'LineWidth', 2);
                hold(ax_top, 'off');
                
                % Plot trigger point on bottom graph + FIRE SMS ALERT + FIRE BUZZER
                % NOTE: this loop runs once per setIdx (1:3), so this fires
                % for the 10kg run, the 8kg run, AND the 6kg run in turn -
                % no payload is skipped.
                %
                % THREE-TIER CLASSIFICATION:
                %   1st trigger (early, < 45s)      -> MOTOR START (blue)
                %   Last trigger in this dataset     -> COLLAPSE    (red)
                %   Any trigger in between            -> CRACK      (orange)
                if i == 1 && elapsed_sec < 45
                    plot(ax_bot, event_time, pks(i), 'v', 'MarkerFaceColor', [0.2 0.6 1], 'MarkerEdgeColor', [0.2 0.6 1], 'MarkerSize', 10);
                    text(ax_bot, event_time, pks(i) + 0.5, sprintf('MOTOR START\n%.2fs\n%.2fHz', elapsed_sec, event_freq), 'Color', [0.2 0.6 1], 'FontWeight', 'bold');
                    sendCollapseSMS(smsEnabled, smsURL, smsOptions, 'MOTOR START', currentName, targetPhone);
                    sendBuzzerCommand(buzzerEnabled, buzzerUdpObj, 'MOTOR START', esp32_IP, esp32_Port);
                elseif i == length(locs)
                    plot(ax_bot, event_time, pks(i), 'rv', 'MarkerFaceColor', 'r', 'MarkerEdgeColor', 'r', 'MarkerSize', 10);
                    text(ax_bot, event_time, pks(i) + 0.5, sprintf('COLLAPSE\n%.2fs\n%.2fHz', elapsed_sec, event_freq), 'Color', 'r', 'FontWeight', 'bold');
                    sendCollapseSMS(smsEnabled, smsURL, smsOptions, 'COLLAPSE', currentName, targetPhone);
                    sendBuzzerCommand(buzzerEnabled, buzzerUdpObj, 'COLLAPSE', esp32_IP, esp32_Port);
                else
                    plot(ax_bot, event_time, pks(i), 'v', 'MarkerFaceColor', [0.93 0.69 0.13], 'MarkerEdgeColor', [0.93 0.69 0.13], 'MarkerSize', 10);
                    text(ax_bot, event_time, pks(i) + 0.5, sprintf('CRACK\n%.2fs\n%.2fHz', elapsed_sec, event_freq), 'Color', [0.93 0.69 0.13], 'FontWeight', 'bold');
                    sendCollapseSMS(smsEnabled, smsURL, smsOptions, 'CRACK', currentName, targetPhone);
                    sendBuzzerCommand(buzzerEnabled, buzzerUdpObj, 'CRACK', esp32_IP, esp32_Port);
                end
            end
        end
        hold off;
        linkaxes([ax_top, ax_bot], 'x');
    end
end
% Clean up the buzzer UDP sender now that all detection loops are done
if exist('buzzerUdpObj', 'var') && ~isempty(buzzerUdpObj)
    clear buzzerUdpObj;
end

disp('Full Unified SHM Pipeline execution complete!');
