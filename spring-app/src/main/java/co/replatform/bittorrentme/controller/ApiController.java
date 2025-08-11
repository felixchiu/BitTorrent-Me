package co.replatform.bittorrentme.controller;

import org.springframework.http.MediaType;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import co.replatform.bittorrentme.model.TorrentModels;
import co.replatform.bittorrentme.service.DownloadService;
import co.replatform.bittorrentme.service.SessionService;
import co.replatform.bittorrentme.service.TorrentService;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

@RestController
public class ApiController {
    private final TorrentService torrentService;
    private final DownloadService downloadService;
    private final SessionService sessionService;

    private Path downloadDir = Path.of("downloads");

    public ApiController(TorrentService torrentService, DownloadService downloadService, SessionService sessionService) throws IOException {
        this.torrentService = torrentService;
        this.downloadService = downloadService;
        this.sessionService = sessionService;
        this.downloadDir = Path.of(sessionService.getSettings().downloadDir);
        Files.createDirectories(this.downloadDir);
    }

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Map<String, Object> upload(@RequestPart("file") MultipartFile file,
                                      @RequestPart(value = "settings", required = false) String settingsJson) throws IOException {
        if (file == null) {
            return Map.of("error", "Invalid file format. Only .torrent files are supported.");
        }
        String original = file.getOriginalFilename();
        if (original == null) {
            return Map.of("error", "Invalid file format. Only .torrent files are supported.");
        }
        if (!StringUtils.hasText(original)) {
            return Map.of("error", "Invalid file format. Only .torrent files are supported.");
        }
        String lower = original.toLowerCase(java.util.Locale.ROOT);
        if (!lower.endsWith(".torrent")) {
            return Map.of("error", "Invalid file format. Only .torrent files are supported.");
        }
        Path temp = Files.createTempFile("torrent", ".torrent");
        file.transferTo(temp);

        TorrentModels.TorrentInfo info = torrentService.parseTorrent(temp);
        Path dlDir = Path.of(sessionService.getSettings().downloadDir);
        Files.createDirectories(dlDir);
        String torrentId = downloadService.createDownload(info, new TorrentModels.DownloadSettings(), dlDir);

        Map<String, Object> resp = new HashMap<>();
        resp.put("message", "Parsed torrent: " + info.name);
        resp.put("torrent_id", torrentId);
        resp.put("name", info.name);
        resp.put("pieces", info.pieces.size());
        resp.put("total_size", info.totalSize);
        resp.put("is_multi_file", info.multiFile);
        resp.put("files", info.files);
        return resp;
    }

    @GetMapping("/files/{torrentId}")
    public Map<String, Object> getFiles(@PathVariable String torrentId) {
        var st = downloadService.get(torrentId);
        if (st == null) return Map.of("error", "Not found");
        return Map.of("files", st.info.files);
    }

    @PostMapping("/files/{torrentId}")
    public Map<String, String> setFiles(@PathVariable String torrentId, @RequestBody Map<String, Boolean> selections) {
        var st = downloadService.get(torrentId);
        if (st == null) return Map.of("error", "Not found");
        if (st.info.multiFile) {
            st.info.files.forEach(f -> {
                Boolean sel = selections.get(f.path);
                if (sel != null) f.selected = sel;
            });
        }
        return Map.of("message", "File selection updated");
    }

    @GetMapping("/status")
    public Map<String, Object> status() {
        Map<String, Object> out = new HashMap<>();
        downloadService.getAll().forEach((id, st) -> {
            Map<String, Object> s = new HashMap<>();
            s.put("torrent_id", id);
            s.put("name", st.info.name);
            s.put("downloading", st.downloading);
            s.put("paused", st.paused);
            s.put("progress", st.progress);
            s.put("download_speed", st.downloadedSize / 1024.0); // approx KB/s
            s.put("upload_speed", 0);
            s.put("downloaded_pieces", (int) Math.round(st.info.pieces.size() * st.progress / 100.0));
            s.put("total_pieces", st.info.pieces.size());
            s.put("total_size", st.info.totalSize);
            s.put("downloaded_size", st.downloadedSize);
            s.put("completed", st.completed);
            s.put("settings", st.settings);
            s.put("is_multi_file", st.info.multiFile);
            s.put("files", st.info.files);
            s.put("queue_position", st.queuePosition);
            out.put(id, s);
        });
        return out;
    }

    @GetMapping("/start/{torrentId}")
    public Map<String, String> start(@PathVariable String torrentId) throws IOException, InterruptedException {
        downloadService.startAsync(torrentId);
        return Map.of("message", "Download started");
    }

    @GetMapping("/pause/{torrentId}")
    public Map<String, String> pause(@PathVariable String torrentId) {
        downloadService.pause(torrentId);
        return Map.of("message", "Download paused");
    }

    @GetMapping("/resume/{torrentId}")
    public Map<String, String> resume(@PathVariable String torrentId) {
        downloadService.resume(torrentId);
        return Map.of("message", "Download resumed");
    }

    @GetMapping("/stop/{torrentId}")
    public Map<String, String> stop(@PathVariable String torrentId) {
        downloadService.stop(torrentId);
        return Map.of("message", "Download stopped");
    }

    @GetMapping("/remove/{torrentId}")
    public Map<String, String> remove(@PathVariable String torrentId) throws IOException {
        boolean ok = downloadService.remove(torrentId);
        return Map.of("message", ok ? "Download removed" : "Not found");
    }

    @PostMapping("/set-download-dir")
    public Map<String, String> setDownloadDir(@RequestBody Map<String, String> req) throws IOException {
        String dir = req.getOrDefault("directory", "downloads");
        downloadDir = Path.of(dir);
        Files.createDirectories(downloadDir);
        var s = sessionService.getSettings();
        s.downloadDir = downloadDir.toString();
        sessionService.updateSettings(s);
        return Map.of("directory", downloadDir.toString());
    }

    @GetMapping("/get-download-dir")
    public Map<String, String> getDownloadDir() {
        return Map.of("directory", sessionService.getSettings().downloadDir);
    }

    // Queueing similar to Transmission's start rules
    @PostMapping("/queue/start/{torrentId}")
    public Map<String, String> queueStart(@PathVariable String torrentId) {
        downloadService.enqueueStart(torrentId);
        return Map.of("message", "Queued to start");
    }

    // Session endpoints (Transmission-like)
    @GetMapping("/session")
    public TorrentModels.SessionSettings getSession() { return sessionService.getSettings(); }

    @PostMapping("/session")
    public Map<String, String> setSession(@RequestBody TorrentModels.SessionSettings settings) {
        sessionService.updateSettings(settings);
        return Map.of("message", "Session updated");
    }

    @GetMapping("/session-stats")
    public TorrentModels.SessionStats getSessionStats() { return sessionService.getStats(); }

    // Queue settings
    @GetMapping("/queue/settings")
    public Map<String, Object> getQueueSettings() {
        return Map.of("max_active_downloads", downloadService.getMaxActiveDownloads());
    }

    @PostMapping("/queue/settings")
    public Map<String, Object> setQueueSettings(@RequestBody Map<String, Integer> req) {
        int max = req.getOrDefault("max_active_downloads", 3);
        downloadService.setMaxActiveDownloads(max);
        return Map.of("max_active_downloads", downloadService.getMaxActiveDownloads());
    }

    // Magnet link support: minimal parse to create a placeholder torrent
    @PostMapping("/add-magnet")
    public Map<String, Object> addMagnet(@RequestBody Map<String, String> req) throws IOException {
        String magnet = req.getOrDefault("magnet", "");
        if (!magnet.startsWith("magnet:?")) return Map.of("error", "Invalid magnet URI");
        // Extract dn (display name) if present
        String name = "Magnet Download";
        try {
            for (String part : magnet.substring("magnet:?".length()).split("&")) {
                if (part.startsWith("dn=")) {
                    name = java.net.URLDecoder.decode(part.substring(3), java.nio.charset.StandardCharsets.UTF_8);
                }
            }
        } catch (Exception ignored) {}
        // Create a synthetic TorrentInfo as placeholder (no real metadata fetch)
        TorrentModels.TorrentInfo info = new TorrentModels.TorrentInfo();
        info.name = name;
        info.totalSize = 500 * 1024L * 1024L; // 500MB placeholder
        info.pieceLength = 256 * 1024; // 256KB
        int numPieces = (int) Math.ceil((double) info.totalSize / info.pieceLength);
        for (int i = 0; i < numPieces; i++) {
            TorrentModels.Piece p = new TorrentModels.Piece();
            p.index = i;
            p.size = (int) Math.min(info.pieceLength, info.totalSize - (long) i * info.pieceLength);
            p.hash = new byte[20];
            info.pieces.add(p);
        }
        String torrentId = downloadService.createDownload(info, new TorrentModels.DownloadSettings(), downloadDir);
        if (sessionService.getSettings().startAddedTorrents) {
            downloadService.enqueueStart(torrentId);
        }
        return Map.of("torrent_id", torrentId, "name", info.name);
    }
}


