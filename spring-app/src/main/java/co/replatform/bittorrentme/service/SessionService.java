package co.replatform.bittorrentme.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import co.replatform.bittorrentme.model.TorrentModels;

import java.io.IOException;
import java.nio.file.*;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class SessionService {
    private final TorrentService torrentService;
    private final DownloadService downloadService;

    private final TorrentModels.SessionSettings settings = new TorrentModels.SessionSettings();
    private final TorrentModels.SessionStats stats = new TorrentModels.SessionStats();

    private final Map<String, Long> lastDownloadedBytesSnapshot = new ConcurrentHashMap<>();
    private Instant sessionStart = Instant.now();

    public SessionService(TorrentService torrentService, DownloadService downloadService,
                          @Value("${bittorrent.download-dir:downloads}") String defaultDownloadDir) {
        this.torrentService = torrentService;
        this.downloadService = downloadService;
        this.settings.downloadDir = defaultDownloadDir;
    }

    public TorrentModels.SessionSettings getSettings() { return settings; }

    public void updateSettings(TorrentModels.SessionSettings newSettings) {
        if (newSettings == null) return;
        // Shallow copy selected fields
        settings.downloadSpeedLimitKb = newSettings.downloadSpeedLimitKb;
        settings.downloadSpeedLimited = newSettings.downloadSpeedLimited;
        settings.uploadSpeedLimitKb = newSettings.uploadSpeedLimitKb;
        settings.uploadSpeedLimited = newSettings.uploadSpeedLimited;
        settings.dhtEnabled = newSettings.dhtEnabled;
        settings.pexEnabled = newSettings.pexEnabled;
        settings.lpdEnabled = newSettings.lpdEnabled;
        settings.utpEnabled = newSettings.utpEnabled;
        settings.encryptionRequired = newSettings.encryptionRequired;
        settings.portForwardingEnabled = newSettings.portForwardingEnabled;
        settings.peerPort = newSettings.peerPort;
        settings.peerPortRandomOnStart = newSettings.peerPortRandomOnStart;
        settings.incompleteDir = newSettings.incompleteDir;
        settings.incompleteDirEnabled = newSettings.incompleteDirEnabled;
        settings.downloadDir = newSettings.downloadDir;
        settings.watchDir = newSettings.watchDir;
        settings.watchDirEnabled = newSettings.watchDirEnabled;
        settings.startAddedTorrents = newSettings.startAddedTorrents;
        settings.trashOriginalTorrentFiles = newSettings.trashOriginalTorrentFiles;
        settings.blocklistUrl = newSettings.blocklistUrl;
        settings.blocklistEnabled = newSettings.blocklistEnabled;
    }

    public TorrentModels.SessionStats getStats() { return stats; }

    @Scheduled(fixedDelay = 1000)
    public void tick() {
        // Queue management
        downloadService.maybeStartQueued();

        // Stats aggregation
        long active = 0;
        long paused = 0;
        long total = 0;
        double downSpeed = 0;
        double upSpeed = 0;
        long downloadedBytes = 0;
        long uploadedBytes = 0;

        for (Map.Entry<String, DownloadService.TorrentState> e : downloadService.getAll().entrySet()) {
            total++;
            var st = e.getValue();
            if (st.downloading) active++;
            if (st.paused) paused++;
            downloadedBytes += st.downloadedSize;
            uploadedBytes += 0; // simulation

            // Rough per-torrent speed estimation from snapshot
            long prev = lastDownloadedBytesSnapshot.getOrDefault(e.getKey(), 0L);
            long delta = Math.max(0, st.downloadedSize - prev);
            lastDownloadedBytesSnapshot.put(e.getKey(), st.downloadedSize);
            downSpeed += delta / 1_024.0; // KB/s
        }

        stats.activeTorrentCount = active;
        stats.pausedTorrentCount = paused;
        stats.totalTorrentCount = total;
        stats.downloadSpeed = downSpeed;
        stats.uploadSpeed = upSpeed;
        stats.downloadedBytes = downloadedBytes;
        stats.uploadedBytes = uploadedBytes;
        stats.secondsActive = Duration.between(sessionStart, Instant.now()).toSeconds();

        // Watch directory scanner (simple polling)
        if (settings.watchDirEnabled && settings.watchDir != null && !settings.watchDir.isBlank()) {
            try {
                scanWatchDir();
            } catch (Exception ignored) { }
        }
    }

    private void scanWatchDir() throws IOException {
        Path dir = Paths.get(settings.watchDir);
        if (!Files.isDirectory(dir)) return;
        try (DirectoryStream<Path> ds = Files.newDirectoryStream(dir, path -> path.toString().endsWith(".torrent"))) {
            for (Path p : ds) {
                // Skip files already processed by renaming convention
                if (p.getFileName().toString().endsWith(".added")) continue;
                try {
                    var info = torrentService.parseTorrent(p);
                    var torrentId = downloadService.createDownload(info, new TorrentModels.DownloadSettings(), Paths.get(settings.downloadDir));
                    if (settings.startAddedTorrents) {
                        downloadService.enqueueStart(torrentId);
                    }
                    if (settings.trashOriginalTorrentFiles) {
                        Files.deleteIfExists(p);
                    } else {
                        Files.move(p, p.resolveSibling(p.getFileName().toString() + ".added"), StandardCopyOption.REPLACE_EXISTING);
                    }
                } catch (Exception ignored) { }
            }
        }
    }
}


