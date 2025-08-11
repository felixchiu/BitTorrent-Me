package co.replatform.bittorrentme.util;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/** Minimal Bencode decoder/encoder for .torrent files. */
public final class Bencode {
    private final byte[] data;
    private int pos = 0;

    private Bencode(byte[] data) { this.data = data; }

    public static Object decode(byte[] data) { return new Bencode(data).parse(); }

    public static byte[] encode(Object value) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        encodeValue(out, value);
        return out.toByteArray();
    }

    private static void encodeValue(ByteArrayOutputStream out, Object v) {
        if (v instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> map = (Map<String, Object>) v;
            out.write('d');
            // Bencode requires keys sorted lexicographically
            for (Map.Entry<String, Object> e : new TreeMap<>(map).entrySet()) {
                byte[] kb = e.getKey().getBytes(StandardCharsets.UTF_8);
                writeBytestring(out, kb);
                encodeValue(out, e.getValue());
            }
            out.write('e');
        } else if (v instanceof List) {
            out.write('l');
            @SuppressWarnings("unchecked")
            List<Object> list = (List<Object>) v;
            for (Object o : list) encodeValue(out, o);
            out.write('e');
        } else if (v instanceof Number) {
            out.write('i');
            byte[] nb = String.valueOf(((Number) v).longValue()).getBytes(StandardCharsets.UTF_8);
            out.write(nb, 0, nb.length);
            out.write('e');
        } else if (v instanceof byte[]) {
            writeBytestring(out, (byte[]) v);
        } else if (v instanceof String) {
            writeBytestring(out, ((String) v).getBytes(StandardCharsets.UTF_8));
        } else if (v == null) {
            writeBytestring(out, new byte[0]);
        } else {
            // fallback to string
            writeBytestring(out, v.toString().getBytes(StandardCharsets.UTF_8));
        }
    }

    private static void writeBytestring(ByteArrayOutputStream out, byte[] b) {
        byte[] len = String.valueOf(b.length).getBytes(StandardCharsets.UTF_8);
        out.write(len, 0, len.length);
        out.write(':');
        out.write(b, 0, b.length);
    }

    private Object parse() {
        byte c = data[pos];
        if (c == 'i') return parseInt();
        if (c == 'l') return parseList();
        if (c == 'd') return parseDict();
        if (c >= '0' && c <= '9') return parseBytes();
        throw new IllegalArgumentException("Invalid bencode at pos " + pos);
    }

    private long parseLong() {
        int start = pos;
        while (pos < data.length && data[pos] != 'e') pos++;
        long val = Long.parseLong(new String(data, start, pos - start, StandardCharsets.UTF_8));
        return val;
    }

    private Long parseInt() {
        pos++; // 'i'
        long v = parseLong();
        if (pos < data.length && data[pos] == 'e') pos++;
        return v;
    }

    private byte[] parseBytes() {
        int start = pos;
        while (data[pos] != ':') pos++;
        int len = Integer.parseInt(new String(data, start, pos - start, StandardCharsets.UTF_8));
        pos++; // ':'
        byte[] out = new byte[len];
        System.arraycopy(data, pos, out, 0, len);
        pos += len;
        return out;
    }

    private List<Object> parseList() {
        pos++; // 'l'
        List<Object> list = new ArrayList<>();
        while (data[pos] != 'e') list.add(parse());
        pos++; // 'e'
        return list;
    }

    private Map<String, Object> parseDict() {
        pos++; // 'd'
        Map<String, Object> map = new LinkedHashMap<>();
        while (data[pos] != 'e') {
            byte[] key = (byte[]) parse();
            String skey = new String(key, StandardCharsets.UTF_8);
            Object val = parse();
            map.put(skey, val);
        }
        pos++; // 'e'
        return map;
    }
}


