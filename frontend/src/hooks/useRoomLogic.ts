import { useEffect, useRef, useState, useContext, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthProvider";
import { RoomSocket } from "../websocket/roomSocket";
import { Role, Question, LeaderboardEntry, RoomViewState } from "../types/room";
import { useGetWSTicketMutation } from "./queries/useGameQueries";

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

    const ticketMutation = useGetWSTicketMutation();

    const getViewState = (): RoomViewState => {
        if (!authenticated && !nameSubmitted) return "ENTER_NAME";
        
        if (question) return "QUESTION";
        
        if (leaderboard.length > 0) {
            return isFinalLeaderboard ? "FINISHED" : "LEADERBOARD";
        }

        return "WAITING";
    };

    const disconnect = useCallback(() => {
        roomSocketRef.current?.disconnect();
        roomSocketRef.current = null;
    }, []);

    const connectRoom = useCallback(async (playerId: string, username?: string) => {
        if (!room_id) {
            return;
        }

        let ticket: string | undefined = undefined;

        if (authenticated) {
            try {
                const response = await ticketMutation.mutateAsync(room_id);
                ticket = response.ticket;
            } catch (err) {
                console.error("Failed to acquire WebSocket access ticket:", err);
                setRedirect("/");
                return;
            }
        }

        const socket = new RoomSocket(room_id, ticket);
        roomSocketRef.current = socket;
        socket.onOpen(() => {
            setConnected(true);
        });

        socket.onClose(() => {
            setConnected(false);
        })

        socket.connect({
            onRole: (role, playerId) => {
                setRole(role);
                playerIdRef.current = playerId;
                
                if (role !== "host") {
                    const finalUsername = username || (keycloak.tokenParsed?.preferred_username as string);
                    if (finalUsername) {
                        socket.join(finalUsername);
                    }
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

                if (code === "ANSWER_ALREADY_SUBMITTED" || code === "FORBIDDEN") {
                    setSelectedAnswer(null);
                }

                if (
                    code === "ROOM_NOT_FOUND" ||
                    code === "ROOM_ALREADY_STARTED" ||
                    code === "PLAYER_ALREADY_CONNECTED"
                ) {
                    setRedirect("/");
                }
            }
        });
    }, [room_id, authenticated, keycloak.tokenParsed]);

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

            connectRoom(playerId, username).catch((err) => {
                console.error("Error connecting to room:", err);
            });
            setNameSubmitted(true);
        }

        return () => {
            disconnect();
        }
    }, [authenticated, room_id, connectRoom, disconnect, keycloak.tokenParsed]);

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