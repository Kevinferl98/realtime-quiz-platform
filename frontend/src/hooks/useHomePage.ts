import { useState, useEffect, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthProvider";
import { Quiz } from "../types/quiz";
import { quizService } from "../services/quizService";

export function useHomePage() {
    const navigate = useNavigate();
    const { keycloak, authenticated } = useContext(AuthContext);

    const [quizzes, setQuizzes] = useState<Quiz[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [roomCode, setRoomCode] = useState<string>("");
    const [page, setPage] = useState<number>(1);
    const [pages, setPages] = useState<number>(1);
    const limit = 10;

    useEffect(() => {
        const loadQuizzes = async () => {
            setLoading(true);
            setError(null);

            try {
                const data = await quizService.getPublicQuizzes(page, limit);
                setQuizzes(data.quizzes || []);
                setPages(data.pages);
            } catch (err: any) {
                setError(err.message || "Error loading quizzes");
            } finally {
                setLoading(false);
            }
        };

        loadQuizzes();
    }, [page]);

    useEffect(() => {
        window.scrollTo(0, 0);
    }, [page]);

    const actions = {
        login: () => keycloak.login(),
        logout: () => keycloak.logout({ redirectUri: window.location.origin }),

        setRoomCode,
        
        joinRoom: () => {
            if (!roomCode.trim()) {
                alert("Please enter a valid room code.");
                return;
            }
            navigate(`/room/${roomCode}`);
        },

        playSolo: (quizId: string) => {
            navigate(`/solo-quiz/${quizId}`);
        },

        createQuiz: () => {
            if (!authenticated) return keycloak.login();
            navigate("/create");
        },

        generateAI: () => {
            if (!authenticated) return keycloak.login();
            navigate("/generate-ai");
        },

        createRoom: () => {
            if (!authenticated) return keycloak.login();
            navigate("/create-room");
        },

        goToMyQuizzes: () => navigate("/my-quizzes"),
        setPage,
    };

    return {
        state: {
            quizzes,
            loading,
            error,
            roomCode,
            page,
            pages,
            authenticated,
            username: keycloak.tokenParsed?.preferred_username,
        },
        actions,
    };
}