-- KEYS[1] = room:{room_id}:players
-- KEYS[2] = room:{room_id}:scores
-- ARGV[1] = player_id
-- ARGV[2] = player_name

local players_key = KEYS[1]
local scores_key = KEYS[2]

local player_id = ARGV[1]
local player_name = ARGV[2]

if redis.call('HEXISTS', players_key, player_id) == 1 then
    return 0
end

redis.call('HSET', players_key, player_id, player_name)
redis.call('ZADD', scores_key, 0, player_id)

return 1