package com.platform.service;

import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;

@Service
public class DeduplicationService {

    private final StringRedisTemplate redisTemplate;
    private static final Duration DEFAULT_DEDUPE_TTL = Duration.ofMinutes(5);

    public DeduplicationService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    /**
     * Checks if this alert/event hash is unique within the sliding TTL window.
     * @return true if this is the FIRST time seeing this event (lock acquired), false if duplicate.
     */
    public boolean acquireDeduplicationLock(String dedupeHash) {
        String key = "dedupe:task:" + dedupeHash;
        Boolean isFirstSeen = redisTemplate.opsForValue().setIfAbsent(key, "LOCKED", DEFAULT_DEDUPE_TTL);
        return Boolean.TRUE.equals(isFirstSeen);
    }

    /**
     * Computes a deterministic SHA-256 fingerprint for the task payload.
     */
    public String computeFingerprint(String source, String payload) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest((source + ":" + payload).getBytes(StandardCharsets.UTF_8));
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) hexString.append('0');
                hexString.append(hex);
            }
            return hexString.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not supported", e);
        }
    }
}
