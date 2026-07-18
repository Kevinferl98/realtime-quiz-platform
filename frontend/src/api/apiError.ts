export class ApiError extends Error {
    readonly status: number;
    readonly data: unknown;

    constructor(
        status: number,
        message: string,
        data?: unknown
    ) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.data = data;
    }
}