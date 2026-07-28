import { useEffect, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../auth/AuthProvider";
import { useMyQuizzeList, useDeleteQuiz } from "./queries/useQuizQueries";

export function useMyQuizzes() {
    const navigate = useNavigate();
    const { keycloak, authenticated } = useContext(AuthContext);

    useEffect(() => {
        if (!authenticated) {
            navigate("/");
            return;
        }
    }, [authenticated, navigate]);

    const { data, isLoading, isError, error } = useMyQuizzeList(authenticated);
    
    const deleteQuizMutation = useDeleteQuiz();

    const actions = {
        logout: () => keycloak.logout({ redirectUri: window.location.origin }),

        goHome: () => navigate("/"),

        playSolo: (quizId: string) => {
            navigate(`/solo-quiz/${quizId}`);
        },

        deleteQuiz: async (quizId: string) => {
            if (!window.confirm("Are you sure you want to delete this quiz?"))
                return;

            deleteQuizMutation.mutate(quizId, {
                onError: (err: any) => {
                    alert(err.message || "Failed to delete quiz");
                }
            });
        }
    };

    return {
        state: {
            myQuizzes: data?.quizzes || [],
            loading: isLoading || deleteQuizMutation.isPending,
            error: isError ? (error as Error).message || "Error loading your quizzes" : null,
            username: keycloak.tokenParsed?.preferred_username
        },
        actions
    };
}