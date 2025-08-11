package co.replatform.bittorrentme.model;

import java.util.ArrayList;
import java.util.List;

public final class TorrentModels {
    public static final class TorrentFile {
        public String path;
        public long length;
        public long offset;
        public boolean selected = true;
    }

    public static final class Piece {
        public int index;
        public int size;
        public byte[] hash;
        public boolean downloaded;
    }

    public static final class TorrentInfo {
        public String name;
        public long totalSize;
        public int pieceLength;
        public List<Piece> pieces = new ArrayList<>();
        public List<TorrentFile> files = new ArrayList<>();
        public boolean multiFile;
        public byte[] infoHash;
    }

    public static final class DownloadSettings {
        public int speedLimit; // KB/s, 0 = unlimited
        public int uploadLimit; // KB/s
        public int maxPeers = 50;
        public int maxConnections = 100;
        public boolean autoStop = true;
        public boolean verifyPieces = true;
        public boolean preAllocate = true;
        public String ratioMode = "global"; // global|per-torrent|unlimited
        public double seedRatioLimit = 2.0;
        public int seedIdleLimitMinutes = 30;
        public String priority = "normal"; // low|normal|high
    }

    public static final class DownloadStatus {
        public String torrentId;
        public String name;
        public boolean downloading;
        public boolean paused;
        public double progress;
        public long downloadedSize;
        public long totalSize;
        public double downloadSpeed;
        public boolean completed;
        public boolean isMultiFile;
        public List<TorrentFile> files = new ArrayList<>();
        public DownloadSettings settings;
        public long uploadedSize;
        public int queuePosition;
    }

    public static final class SessionSettings {
        public int downloadSpeedLimitKb = 0; // 0 = unlimited
        public boolean downloadSpeedLimited = false;
        public int uploadSpeedLimitKb = 0;
        public boolean uploadSpeedLimited = false;
        public boolean dhtEnabled = true;
        public boolean pexEnabled = true;
        public boolean lpdEnabled = true;
        public boolean utpEnabled = true;
        public boolean encryptionRequired = false;
        public boolean portForwardingEnabled = true; // UPnP/NAT-PMP
        public int peerPort = 51413;
        public boolean peerPortRandomOnStart = true;
        public String incompleteDir = "downloads/.incomplete";
        public boolean incompleteDirEnabled = false;
        public String downloadDir = "downloads";
        public String watchDir = "";
        public boolean watchDirEnabled = false;
        public boolean startAddedTorrents = true;
        public boolean trashOriginalTorrentFiles = false;
        public String blocklistUrl = "";
        public boolean blocklistEnabled = false;
    }

    public static final class SessionStats {
        public long activeTorrentCount;
        public long pausedTorrentCount;
        public long totalTorrentCount;
        public double downloadSpeed;
        public double uploadSpeed;
        public long downloadedBytes;
        public long uploadedBytes;
        public long secondsActive;
    }
}


