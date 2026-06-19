import keycloak from "../auth/keycloak";
import { CONFIG } from "../config";

export async function apiFetch<T = any>(
    endpoint: string, 
    options: RequestInit = {},
    requireAuth: boolean = false
): Promise<T> {
    const fullUrl = `${CONFIG.API_BASE}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

    const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...(options.headers as Record<string, string> || {}),
    };

    if (requireAuth) {
        if (!keycloak.authenticated) {
            throw new Error("User not authenticated");
        }
        await keycloak.updateToken(30);

        headers["Authorization"] = `Bearer ${keycloak.token}`;
    }

    const response = await fetch(fullUrl, {
        ...options,
        headers
    });

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`HTTP ${response.status}: ${text}`);
    }
    
    return response.json()
}