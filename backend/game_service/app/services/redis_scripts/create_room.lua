-- KEYS[1] = room:{room_id}
-- KEYS[2] = room:{room_id}:questions

-- ARGV[1] = room_id
-- ARGV[2] = owner_id
-- ARGV[3] = quiz_id
-- ARGV[4] = questions JSON
-- ARGV[5] = TTL in seconds

if redis.call('EXISTS', KEYS[1]) == 1 then
    return 0
end

redis.call('HSET', KEYS[1],
    'room_id', ARGV[1],
    'owner_id', ARGV[2],
    'quiz_id', ARGV[3],
    'status', 'CREATED',
    'current_question_index', '0',
)

redis.call('SET', KEYS[2], ARGV[4])

redis.call('EXPIRE', KEYS[1], ARGV[5])
redis.call('EXPIRE', KEYS[2], ARGV[5])

return 1