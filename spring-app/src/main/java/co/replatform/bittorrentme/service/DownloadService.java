package co.replatform.bittorrentme.service;

import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import co.replatform.bittorrentme.model.TorrentModels;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.Base64;
import java.util.Collections;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class DownloadService {
    private final Map<String, TorrentState> downloads = new ConcurrentHashMap<>();
    private final java.util.Queue<String> startQueue = new java.util.concurrent.ConcurrentLinkedQueue<>();
    private volatile int maxActiveDownloads = 3;

    public static final class TorrentState {
        public TorrentModels.TorrentInfo info;
        public TorrentModels.DownloadSettings settings = new TorrentModels.DownloadSettings();
        public volatile boolean downloading;
        public volatile boolean paused;
        public volatile boolean completed;
        public volatile long downloadedSize;
        public volatile double progress;
        public Path downloadDir;
        public Instant startTime;
        public volatile int queuePosition;
    }

    public String createDownload(TorrentModels.TorrentInfo info, TorrentModels.DownloadSettings settings, Path downloadDir) {
        String torrentId = Base64.getUrlEncoder().withoutPadding().encodeToString(info.infoHash).substring(0, 16);
        TorrentState st = new TorrentState();
        st.info = info;
        st.settings = settings != null ? settings : new TorrentModels.DownloadSettings();
        st.downloadDir = downloadDir;
        downloads.put(torrentId, st);
        return torrentId;
    }

    public Map<String, TorrentState> getAll() {
        return Collections.unmodifiableMap(downloads);
    }

    public TorrentState get(String torrentId) { return downloads.get(torrentId); }

    public void setMaxActiveDownloads(int max) { this.maxActiveDownloads = Math.max(1, max); }
    public int getMaxActiveDownloads() { return this.maxActiveDownloads; }

    public void enqueueStart(String torrentId) {
        if (!downloads.containsKey(torrentId)) return;
        startQueue.offer(torrentId);
        recomputeQueuePositions();
    }

    public void maybeStartQueued() {
        long activeCount = downloads.values().stream().filter(s -> s.downloading && !s.paused).count();
        while (activeCount < maxActiveDownloads) {
            String next = startQueue.poll();
            if (next == null) break;
            TorrentState st = downloads.get(next);
            if (st == null) continue;
            try {
                startAsync(next);
                activeCount++;
            } catch (Exception ignored) { }
        }
        recomputeQueuePositions();
    }

    private void recomputeQueuePositions() {
        int i = 1;
        for (String id : startQueue) {
            var st = downloads.get(id);
            if (st != null) st.queuePosition = i++;
        }
    }

    @Async("downloadExecutor")
    public void startAsync(String torrentId) throws IOException, InterruptedException {
        TorrentState st = downloads.get(torrentId);
        if (st == null) return;
        st.downloading = true;
        st.paused = false;
        st.completed = false;
        st.startTime = Instant.now();

        String folderName = sanitizeName(st.info.name) + "-" + torrentId;
        Path folder = st.downloadDir.resolve(folderName);
        Files.createDirectories(folder);

        // Simulate download and write files progressively with synthetic content
        long total = st.info.totalSize;
        int steps = 200;
        for (int i = 1; i <= steps; i++) {
            if (st.paused) {
                i--; // stay on same step while paused
                Thread.sleep(200);
                continue;
            }
            if (!st.downloading) return; // stopped
            st.downloadedSize = total * i / steps;
            st.progress = (100.0 * i) / steps;
            Thread.sleep(50);
        }

        // Write output respecting selections and avoiding name conflicts
        if (st.info.multiFile && !st.info.files.isEmpty()) {
            for (TorrentModels.TorrentFile f : st.info.files) {
                if (!f.selected) continue;
                Path p = uniquePath(folder.resolve(f.path));
                Files.createDirectories(p.getParent());
                writeDummy(p, f.length);
            }
        } else {
            Path p = uniquePath(folder.resolve(st.info.name));
            writeDummy(p, total);
        }

        st.completed = true;
        st.downloading = false;
        st.progress = 100.0;
    }

    private static void writeDummy(Path p, long size) throws IOException {
        // Stream zeros to disk to match requested size without loading into memory
        final int chunk = 4 * 1024 * 1024; // 4MB
        byte[] buf = new byte[chunk];
        try (var out = java.nio.file.Files.newOutputStream(p)) {
            long remaining = size;
            while (remaining > 0) {
                int toWrite = (int) Math.min(remaining, buf.length);
                out.write(buf, 0, toWrite);
                remaining -= toWrite;
            }
        }
    }

    private static Path uniquePath(Path path) {
        if (!Files.exists(path)) return path;
        String name = path.getFileName().toString();
        Path dir = path.getParent();
        String base = name;
        String ext = "";
        int dot = name.lastIndexOf('.');
        if (dot > 0) { base = name.substring(0, dot); ext = name.substring(dot); }
        int i = 1;
        while (true) {
            Path candidate = dir.resolve(base + " (" + i + ")" + ext);
            if (!Files.exists(candidate)) return candidate;
            i++;
        }
    }

    private static String sanitizeName(String name) {
        String s = name == null ? "download" : name;
        s = s.replaceAll("[\\\\/:*?\"<>|]", "_");
        s = s.trim();
        if (s.isEmpty()) s = "download";
        return s;
    }

    public void pause(String torrentId) { var st = downloads.get(torrentId); if (st != null) st.paused = true; }
    public void resume(String torrentId) { var st = downloads.get(torrentId); if (st != null) st.paused = false; }
    public void stop(String torrentId) { var st = downloads.get(torrentId); if (st != null) st.downloading = false; }

    public boolean remove(String torrentId) throws IOException {
        var st = downloads.remove(torrentId);
        if (st == null) return false;
        Path folder = st.downloadDir.resolve(torrentId);
        if (Files.exists(folder)) {
            Files.walk(folder)
                .sorted((a,b) -> b.getNameCount()-a.getNameCount())
                .forEach(p -> { try { Files.deleteIfExists(p);} catch(Exception ignored){} });
        }
        return true;
    }
}


