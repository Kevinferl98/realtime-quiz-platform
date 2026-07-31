import { useState, useEffect, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthProvider";
import { usePublicQuizzes } from "../hooks/queries/useQuizQueries";

export function useHomePage() {
    const navigate = useNavigate();
    const { keycloak, authenticated } = useContext(AuthContext);

    const [roomCode, setRoomCode] = useState<string>("");
    const [page, setPage] = useState<number>(1);
    const limit = 10;

    const { data, isLoading, isError, error } = usePublicQuizzes(page, limit); 

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
            quizzes: data?.quizzes || [],
            loading: isLoading,
            error: isError ? (error as Error).message || "Error loading quizzes" : null,
            roomCode,
            page,
            pages: data?.pages || 1,
            authenticated,
            username: keycloak.tokenParsed?.preferred_username,
        },
        actions,
    };
}