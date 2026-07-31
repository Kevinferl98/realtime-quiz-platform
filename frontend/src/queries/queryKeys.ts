export const queryKeys = {
    quizzes: {
        all: ["quizzes"] as const,
        lists: () => [...queryKeys.quizzes.all, "list"] as const,
        public: (page: number, limit: number) => [...queryKeys.quizzes.lists(), "public", page, limit] as const,
        mine: () => [...queryKeys.quizzes.lists(), "mine"] as const,
        details: () => [...queryKeys.quizzes.all, "detail"] as const,
        detail: (id: string) => [...queryKeys.quizzes.details(), id] as const
    }
};