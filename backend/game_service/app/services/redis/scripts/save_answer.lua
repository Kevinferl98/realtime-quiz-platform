-- KEYS[1] = room:{room_id}
-- KEYS[2] = room:{room_id}:answers:{question_index}

-- ARGV[1] = player_id
-- ARGV[2] = room_answer_json
-- ARGV[3] = question_index

local room_key = KEYS[1]
local answers_key = KEYS[2]

local player_id = ARGV[1]
local room_answer_json = ARGV[2]
local target_question_index = ARGV[3]

if redis.call("EXISTS", room_key) == 0 then
    return 0 -- ROOM_NOT_FOUND
end

local current_idx = redis.call("HGET", room_key, "current_question_index")
local q_state = redis.call("HGET", room_key, "question_state")

if current_idx ~= target_question_index or q_state ~= "OPEN" then
    return 2 -- QUESTION_CLOSED
end

local set_result = redis.call("HSETNX", answers_key, player_id, room_answer_json)

if set_result == 0 then
    return 3 -- ALREADY_SUBMITTED
end

redis.call("EXPIRE", answers_key, 300, "NX")
return 1 -- SAVED