export const queryKeys = {
    quizzes: {
        all: ["quizzes"] as const,
        public: (page: number, limit: number) => ["quizzes", "public", { page, limit}] as const,
        mine: () => ["quizzes", "mine"] as const,
        detail: (id: string) => ["quizzes", id] as const,
    }
};