-- KEYS[1] = room:{room_id}
-- KEYS[2] = room:{room_id}:questions
-- KEYS[3] = room:{room_id}:players
-- KEYS[4] = room:{room_id}:scores
-- ARGV[1] = owner_id

if redis.call("HGET", KEYS[1], "status") ~= "CREATED" then
    return 0
end

if redis.call("HGET", KEYS[1], "owner_id") ~= ARGV[1] then
    return 0
end

redis.call("DEL", KEYS[1], KEYS[2], KEYS[3], KEYS[4])
return 1