-- KEYS[1] = room:{room_id}

if redis.call("HGET", KEYS[1], "status") ~= "CREATED" then
    return 0
end

redis.call("HSET", KEYS[1], "status", "STARTED")
return 1