class RedisKeys:
    PREFIX = "room"
    CHANNEL_PREFIX = "room_"

    @staticmethod
    def room(room_id: str) -> str:
        return f"{RedisKeys.PREFIX}:{room_id}"

    @staticmethod
    def questions(room_id: str) -> str:
        return f"{RedisKeys.room(room_id)}:questions"

    @staticmethod
    def players(room_id: str) -> str:
        return f"{RedisKeys.room(room_id)}:players"

    @staticmethod
    def scores(room_id: str) -> str:
        return f"{RedisKeys.room(room_id)}:scores"

    @staticmethod
    def answers(room_id: str, question_index: int) -> str:
        return f"{RedisKeys.room(room_id)}:answers:{question_index}"

    @staticmethod
    def room_channel(room_id: str) -> str:
        return f"{RedisKeys.CHANNEL_PREFIX}{room_id}"

    @staticmethod
    def room_channels_pattern() -> str:
        return f"{RedisKeys.CHANNEL_PREFIX}*"