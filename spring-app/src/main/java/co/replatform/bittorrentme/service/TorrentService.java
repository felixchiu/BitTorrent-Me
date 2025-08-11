package com.bittorrentme.service;

import com.bittorrentme.model.TorrentModels;
import org.apache.commons.codec.digest.DigestUtils;
import com.bittorrentme.util.Bencode;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

@Service
public class TorrentService {

    public TorrentModels.TorrentInfo parseTorrent(Path torrentFile) throws IOException {
        byte[] data = Files.readAllBytes(torrentFile);
        @SuppressWarnings("unchecked")
        var root = (java.util.Map<String, Object>) Bencode.decode(data);
        @SuppressWarnings("unchecked")
        var info = (java.util.Map<String, Object>) root.get("info");

        byte[] infoBytes = Bencode.encode(info);
        byte[] infoHash = DigestUtils.sha1(infoBytes);

        TorrentModels.TorrentInfo ti = new TorrentModels.TorrentInfo();
        ti.name = new String((byte[]) info.getOrDefault("name", torrentFile.getFileName().toString()));
        ti.pieceLength = (int) ((Long) info.get("piece length")).longValue();
        byte[] piecesConcat = (byte[]) info.get("pieces");
        ti.multiFile = info.containsKey("files");
        ti.infoHash = infoHash;

        long totalSize = 0L;
        if (ti.multiFile) {
            @SuppressWarnings("unchecked")
            var files = (java.util.List<java.util.Map<String, Object>>) info.get("files");
            long offset = 0;
            for (var f : files) {
                @SuppressWarnings("unchecked")
                var pathParts = (java.util.List<Object>) f.get("path");
                StringBuilder sb = new StringBuilder();
                for (int i = 0; i < pathParts.size(); i++) {
                    if (i > 0) sb.append('/');
                    Object part = pathParts.get(i);
                    if (part instanceof byte[]) sb.append(new String((byte[]) part));
                    else sb.append(part.toString());
                }
                TorrentModels.TorrentFile tf = new TorrentModels.TorrentFile();
                tf.path = sb.toString();
                tf.length = ((Long) f.get("length")).longValue();
                tf.offset = offset;
                ti.files.add(tf);
                totalSize += tf.length;
                offset += tf.length;
            }
        } else {
            totalSize = ((Long) info.get("length")).longValue();
        }
        ti.totalSize = totalSize;

        int numPieces = (int) Math.ceil((double) ti.totalSize / ti.pieceLength);
        for (int i = 0; i < numPieces; i++) {
            TorrentModels.Piece p = new TorrentModels.Piece();
            p.index = i;
            p.size = (int) Math.min(ti.pieceLength, ti.totalSize - (long) i * ti.pieceLength);
            int start = i * 20;
            byte[] hash = new byte[20];
            System.arraycopy(piecesConcat, start, hash, 0, Math.min(20, piecesConcat.length - start));
            p.hash = hash;
            ti.pieces.add(p);
        }

        return ti;
    }
}


