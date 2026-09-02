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

    const [role, setRole] = useState<Role>("player");
    const [players, setPlayers] = useState<string[]>([]);
    const [question, setQuestion] = useState<Question | null>(null);
    const [timer, setTimer] = useState<number>(0);
    const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);

    const [connected, setConnected] = useState(false);
    const connectionGenerationRef = useRef(0);
    const connectingRef = useRef(false);

    const [nameInput, setNameInput] = useState("");
    const [nameSubmitted, setNameSubmitted] = useState(false);

    const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
    const [correctAnswer, setCorrectAnswer] = useState<string | null>(null);

    const [isFinalLeaderboard, setIsFinalLeaderboard] = useState(false);
    const [totalTime, setTotalTime] = useState<number>(15);

    const [redirect, setRedirect] = useState<string | null>(null);

    const { mutateAsync: getWSTicket } = useGetWSTicketMutation();
    const playerId = keycloak.tokenParsed?.sub as string | undefined;
    const authenticatedUsername = keycloak.tokenParsed?.preferred_username as string | undefined;

    const getViewState = (): RoomViewState => {
        if (!authenticated && !nameSubmitted) return "ENTER_NAME";
        
        if (question) return "QUESTION";
        
        if (leaderboard.length > 0) {
            return isFinalLeaderboard ? "FINISHED" : "LEADERBOARD";
        }

        return "WAITING";
    };

    const disconnect = useCallback(() => {
        connectionGenerationRef.current += 1;
        connectingRef.current = false;
        roomSocketRef.current?.disconnect();
        roomSocketRef.current = null;
        setConnected(false);
    }, []);

    const connectRoom = useCallback(async (username?: string) => {
        if (!room_id || connectingRef.current || roomSocketRef.current) {
            return;
        }

        const generation = connectionGenerationRef.current;
        connectingRef.current = true;
        let ticket: string | undefined = undefined;

        if (authenticated) {
            try {
                const response = await getWSTicket(room_id);
                ticket = response.ticket;
            } catch (err) {
                console.error("Failed to acquire WebSocket access ticket:", err);
                if (generation === connectionGenerationRef.current) {
                    setRedirect("/");
                }
                connectingRef.current = false;
                return;
            }
        }

        if (generation !== connectionGenerationRef.current) {
            connectingRef.current = false;
            return;
        }

        const socket = new RoomSocket(room_id, ticket);
        roomSocketRef.current = socket;
        connectingRef.current = false;
        socket.onOpen(() => {
            if (roomSocketRef.current !== socket) return;
            setConnected(true);
        });

        socket.onClose(() => {
            if (roomSocketRef.current !== socket) return;
            roomSocketRef.current = null;
            setConnected(false);
        });

        socket.connect({
            onRole: (role) => {
                setRole(role);
                
                if (role !== "host") {
                    const finalUsername = username || authenticatedUsername;
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
            },

            onConnectionError: (error) => {
                if (roomSocketRef.current !== socket) return;
                console.error("WebSocket connection error:", error);
                setConnected(false);
                alert(error.message);
            }
        });
    }, [room_id, authenticated, authenticatedUsername, getWSTicket]);

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
            if (!playerId) {
                setRedirect("/");
                return;
            }


            connectRoom(authenticatedUsername).catch((err) => {
                console.error("Error connecting to room:", err);
            });
            setNameSubmitted(true);
        }

        return () => {
            disconnect();
        }
    }, [authenticated, room_id, playerId, authenticatedUsername, connectRoom, disconnect]);

    // Redirect
    useEffect(() => {
        if (redirect) navigate(redirect);
    }, [redirect, navigate]);

    const handleSubmitName = () => {
        if (!nameInput.trim() || connectingRef.current || roomSocketRef.current) {
            return;
        }

        connectRoom(nameInput.trim()).catch((err) => {
            console.error("Error connecting guest to room:", err);
        });
        setNameSubmitted(true);
    };

    const handleStart = () => {
        if (!connected) return;
        roomSocketRef.current?.start();
    };

    const handleAnswer = (answer: string) => {
        if (!connected || selectedAnswer) {
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