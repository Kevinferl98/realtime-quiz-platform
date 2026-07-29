import { useState, useEffect, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthProvider";
import { usePublicQuizzes } from "./queries/useQuizQueries";
import { useCreateRoom } from "./queries/useGameQueries";

export function useCreateGameRoom() {
    const navigate = useNavigate();
    const { keycloak, authenticated } = useContext(AuthContext);

    const [page, setPage] = useState<number>(1);
    const limit = 10;
    
    useEffect(() => {
        if (!authenticated) {
            keycloak.login();
        }
    }, [authenticated, keycloak]);

    const { data, isLoading, isError, error } = usePublicQuizzes(page, limit, {
        enabled: authenticated
    });
    
    const createRoomMutation = useCreateRoom();

    useEffect(() => {
        window.scrollTo(0, 0);
    }, [page]);

    const actions = {
        goHome: () => navigate("/"),

        logout: () => keycloak.logout({ redirectUri: window.location.origin }),

        createRoom: async (quizId: string) => {
            createRoomMutation.mutate(quizId, {
                onSuccess: (room) => {
                    navigate(`/room/${room.room_id}`);
                }
            });
        },

        setPage
    };

    return {
        state: {
            quizzes: data?.quizzes || [],
            loading: isLoading,
            error: isError ? (error as Error).message || "Error loading quizzes" : null,
            creatingRoomId: createRoomMutation.isPending ? createRoomMutation.variables : null,
            authenticated,
            page,
            pages: data?.pages || 1
        },
        actions
    };
}