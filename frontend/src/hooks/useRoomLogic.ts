import { useEffect, useRef, useState, useContext } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthProvider";
import { RoomSocket } from "../websocket/roomSocket";
import { Role, Question, LeaderboardEntry, RoomViewState } from "../types/room";

export function useRoomLogic() {
    const { room_id } = useParams();
    const navigate = useNavigate();
    const { keycloak, authenticated } = useContext(AuthContext);

    const roomSocketRef = useRef<RoomSocket | null>(null);
    const playerIdRef = useRef<string>("");

    const [role, setRole] = useState<Role>("player");
    const [players, setPlayers] = useState<string[]>([]);
    const [question, setQuestion] = useState<Question | null>(null);
    const [timer, setTimer] = useState<number>(0);
    const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);

    const [connected, setConnected] = useState(false);

    const [nameInput, setNameInput] = useState("");
    const [nameSubmitted, setNameSubmitted] = useState(false);

    const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
    const [correctAnswer, setCorrectAnswer] = useState<string | null>(null);

    const [isFinalLeaderboard, setIsFinalLeaderboard] = useState(false);
    const [totalTime, setTotalTime] = useState<number>(15);

    const [redirect, setRedirect] = useState<string | null>(null);

    const getViewState = (): RoomViewState => {
        if (!authenticated && !nameSubmitted) return "ENTER_NAME";
        
        if (question) return "QUESTION";
        
        if (leaderboard.length > 0) {
            return isFinalLeaderboard ? "FINISHED" : "LEADERBOARD";
        }

        return "WAITING";
    };

    const disconnect = () => {
        roomSocketRef.current?.disconnect();
        roomSocketRef.current = null;
    }

    const connectRoom = (playerId: string, username?: string) => {
        if (!room_id) {
            return;
        }

        const socket = new RoomSocket(room_id, authenticated ? keycloak.token : undefined);
        roomSocketRef.current = socket;
        socket.onOpen(() => {
            setConnected(true);

            if (username && role !== "host") {
                socket.join(username);
            }
        });

        socket.onClose(() => {
            setConnected(false);
        })

        socket.connect({
            onRole: (role, playerId) => {
                setRole(role);
                playerIdRef.current = playerId;
                
                if (authenticated && role !== "host") {
                    socket.join(keycloak.tokenParsed?.preferred_username as string);
                }
            },

            onPlayersChanged: (players) => {
                setPlayers(players);
            },

            onQuestion: (question) => {
                setQuestion(question);
                setLeaderboard([]);
                setSelectedAnswer(null);
                setCorrectAnswer(null);

                const duration = question.duration ?? 15;
                setTimer(duration);
                setTotalTime(duration);
            },

            onTimer: (seconds) => {
                setTimer(seconds);
            },

            onAnswerResult: (answer) => {
                setCorrectAnswer(answer);
            },

            onLeaderboard: (leaderboard, final) => {
                setQuestion(null);
                setLeaderboard(leaderboard);
                setIsFinalLeaderboard(final);
            },

            onError: (code, message) => {
                alert(message);

                if (code == "ROOM_NOT_FOUND" || code == "ROOM_ALREADY_STARTED") {
                    setRedirect("/");
                }
            }
        });
    };

    // Timer countdown
    useEffect(() => {
        if (!question) {
            return;
        }

        const interval = setInterval(() => {
            setTimer((t) => {
                if (t <= 1 || correctAnswer) {
                    clearInterval(interval);
                    return t;
                }
                return t - 1;
            });
        }, 1000);

        return () => clearInterval(interval);
    }, [question, correctAnswer]);

    // Auth auto join
    useEffect(() => {
        if (!room_id) {
            return;
        }

        if (authenticated) {
            const playerId = keycloak.tokenParsed?.sub as string;
            const username = keycloak.tokenParsed?.preferred_username as string;
            playerIdRef.current = playerId;
            connectRoom(playerId, username);
            setNameSubmitted(true);
        }

        return () => {
            disconnect();
        }
    }, [authenticated, room_id]);

    // Redirect
    useEffect(() => {
        if (redirect) navigate(redirect);
    }, [redirect, navigate]);

    const handleSubmitName = () => {
        if (!nameInput.trim()) {
            return;
        }

        const uuid = crypto.randomUUID();
        playerIdRef.current = uuid;
        connectRoom(uuid, nameInput.trim());
        setNameSubmitted(true);
    };

    const handleStart = () => {
        roomSocketRef.current?.start();
    };

    const handleAnswer = (answer: string) => {
        if (selectedAnswer) {
            return;
        }

        setSelectedAnswer(answer);
        roomSocketRef.current?.answer(answer);
    };

    const disconnectAndGoHome = () => {
        disconnect();
        navigate("/");
    };

    return {
        state: {
            room_id,
            role,
            players,
            question,
            timer,
            leaderboard,
            nameInput,
            nameSubmitted,
            selectedAnswer,
            correctAnswer,
            isFinalLeaderboard,
            totalTime,
            authenticated,
            viewState: getViewState()
        },
        actions: {
            setNameInput,
            handleSubmitName,
            handleStart,
            handleAnswer,
            disconnectAndGoHome
        }
    };
}