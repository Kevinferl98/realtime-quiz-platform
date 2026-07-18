import keycloak from "../auth/keycloak";
import { CONFIG } from "../config";
import { ApiError } from "./apiError";

export interface ApiRequestOptions extends RequestInit {
    requireAuth?: boolean;
}

export async function apiClient<T>(endpoint: string, options: ApiRequestOptions = {}): Promise<T> {
    const {
        requireAuth = false,
        headers,
        ...fetchOptions
    } = options;

    const url = `${CONFIG.API_BASE}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

    const requestHeaders = new Headers(headers);
    requestHeaders.set("Content-Type", "application/json");

    if (requireAuth) {
        if (!keycloak.authenticated) {
            throw new ApiError(
                401,
                "User not authenticated"
            );
        }

        await keycloak.updateToken(30);

        requestHeaders.set(
            "Authorization",
            `Bearer ${keycloak.token}`
        );
    }

    const response = await fetch(url,{
        ...fetchOptions,
        headers: requestHeaders
    });

    let responseBody: unknown;

    const contentType = response.headers.get("Content-Type");
    if (contentType?.includes("application/json")) {
        responseBody = await response.json();
    } else {
        responseBody = await response.text();
    }

    if (!response.ok) {
        throw new ApiError(response.status, response.statusText, responseBody);
    }

    return responseBody as T;
}