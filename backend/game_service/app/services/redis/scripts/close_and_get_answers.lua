-- KEYS[1] = room:{room_id}
-- KEYS[2] = room:{room_id}:answers:{question_index}

local room_key = KEYS[1]
local answers_key = KEYS[2]

if redis.call("EXISTS", room_key) == 0 then
    return {}
end

redis.call("HSET", room_key, "question_state", "CLOSED")

local answers = redis.call("HGETALL", answers_key)

return answers