import { useState, useEffect, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthProvider";
import { Quiz } from "../types/quiz";
import { gameService } from "../services/gameService";
import { quizService } from "../services/quizService";

export function useCreateGameRoom() {
    const navigate = useNavigate();
    const { keycloak, authenticated } = useContext(AuthContext);

    const [quizzes, setQuizzes] = useState<Quiz[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [creatingRoomId, setCreatingRoomId] = useState<string | null>(null);
    const [page, setPage] = useState<number>(1);
    const [pages, setPages] = useState<number>(1);
    const limit = 10;

    useEffect(() => {
        if (!authenticated) {
            keycloak.login();
        }
    }, [authenticated, keycloak]);

    useEffect(() => {
        const loadQuizzes = async () => {
            setLoading(true);
            setError(null);

            try {
                const data = await quizService.getPublicQuizzes(page, limit);
                setQuizzes(data.quizzes || []);
                setPages(data.pages);
            } catch(err: any) {
                setError(err.message || "Error loading quizzes");
            } finally {
                setLoading(false);
            }
        };

        if (authenticated) {
            loadQuizzes();
        }
    }, [authenticated, page]);

    useEffect(() => {
        window.scrollTo(0, 0);
    }, [page]);

    const actions = {
        goHome: () => navigate("/"),

        logout: () => keycloak.logout({ redirectUri: window.location.origin }),

        createRoom: async (quizId: string) => {
            try {
                setCreatingRoomId(quizId);

                const room = await gameService.createRoom(quizId);

                navigate(`/room/${room.room_id}`);
            } catch (err: any) {
                alert(err.message || "Error creating room");
            } finally {
                setCreatingRoomId(null);
            }
        },

        setPage
    };

    return {
        state: {
            quizzes,
            loading,
            error,
            creatingRoomId,
            authenticated,
            page,
            pages
        },
        actions
    };
}