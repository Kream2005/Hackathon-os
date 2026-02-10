(globalThis.TURBOPACK || (globalThis.TURBOPACK = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/Hackathon-os/incident-platform/services/web-ui/lib/utils.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "cn",
    ()=>cn
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$clsx$40$2$2e$1$2e$1$2f$node_modules$2f$clsx$2f$dist$2f$clsx$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/clsx@2.1.1/node_modules/clsx/dist/clsx.mjs [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$tailwind$2d$merge$40$2$2e$6$2e$0$2f$node_modules$2f$tailwind$2d$merge$2f$dist$2f$bundle$2d$mjs$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/tailwind-merge@2.6.0/node_modules/tailwind-merge/dist/bundle-mjs.mjs [app-client] (ecmascript)");
;
;
function cn(...inputs) {
    return (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$tailwind$2d$merge$40$2$2e$6$2e$0$2f$node_modules$2f$tailwind$2d$merge$2f$dist$2f$bundle$2d$mjs$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__["twMerge"])((0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$clsx$40$2$2e$1$2e$1$2f$node_modules$2f$clsx$2f$dist$2f$clsx$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__["clsx"])(inputs));
}
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/Hackathon-os/incident-platform/services/web-ui/lib/api-client.ts [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

/**
 * API Client -- fetches from the FastAPI API Gateway.
 *
 * Browser-side: NEXT_PUBLIC_API_GATEWAY_URL (defaults to http://localhost:8080)
 * Server-side:  API_GATEWAY_URL            (defaults to http://api-gateway:8080 for Docker)
 *
 * No mock fallback -- all data comes from the real backend services.
 */ __turbopack_context__.s([
    "alertsFetcher",
    ()=>alertsFetcher,
    "apiFetch",
    ()=>apiFetch,
    "createIncident",
    ()=>createIncident,
    "createSchedule",
    ()=>createSchedule,
    "deleteSchedule",
    ()=>deleteSchedule,
    "fetcher",
    ()=>fetcher,
    "getIncidentSummary",
    ()=>getIncidentSummary,
    "getServicesHealth",
    ()=>getServicesHealth,
    "incidentsFetcher",
    ()=>incidentsFetcher,
    "ingestAlert",
    ()=>ingestAlert,
    "listEscalations",
    ()=>listEscalations,
    "removeOverride",
    ()=>removeOverride,
    "sendNotification",
    ()=>sendNotification,
    "setOverride",
    ()=>setOverride,
    "triggerEscalation",
    ()=>triggerEscalation,
    "updateIncident",
    ()=>updateIncident
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = /*#__PURE__*/ __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/next@16.1.6_react-dom@19.2.3_react@19.2.3__react@19.2.3/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
const GATEWAY_URL = ("TURBOPACK compile-time truthy", 1) ? __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"].env.NEXT_PUBLIC_API_GATEWAY_URL ?? "http://localhost:8080" : "TURBOPACK unreachable";
async function apiFetch(path, options) {
    const res = await fetch(`${GATEWAY_URL}${path}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...options?.headers ?? {}
        }
    });
    if (!res.ok) {
        const body = await res.text().catch(()=>"");
        throw new Error(`API error ${res.status}: ${res.statusText} — ${body}`);
    }
    return await res.json();
}
const fetcher = (path)=>apiFetch(path);
const incidentsFetcher = async (path)=>{
    const data = await apiFetch(path);
    // If the response is a paginated wrapper, unwrap it
    if (data && typeof data === "object" && Array.isArray(data.incidents)) {
        return data.incidents;
    }
    return data;
};
const alertsFetcher = async (path)=>{
    const data = await apiFetch(path);
    if (data && typeof data === "object" && Array.isArray(data.alerts)) {
        return data.alerts;
    }
    return data;
};
async function createIncident(body) {
    return apiFetch("/api/v1/incidents", {
        method: "POST",
        body: JSON.stringify(body)
    });
}
async function updateIncident(id, body) {
    return apiFetch(`/api/v1/incidents/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body)
    });
}
async function getIncidentSummary() {
    return apiFetch("/api/v1/incidents/stats/summary");
}
async function ingestAlert(body) {
    return apiFetch("/api/v1/alerts", {
        method: "POST",
        body: JSON.stringify(body)
    });
}
async function createSchedule(body) {
    return apiFetch("/api/v1/schedules", {
        method: "POST",
        body: JSON.stringify(body)
    });
}
async function deleteSchedule(team) {
    await apiFetch(`/api/v1/schedules/${encodeURIComponent(team)}`, {
        method: "DELETE"
    });
}
async function setOverride(body) {
    return apiFetch("/api/v1/oncall/override", {
        method: "POST",
        body: JSON.stringify(body)
    });
}
async function removeOverride(team) {
    await apiFetch(`/api/v1/oncall/override/${encodeURIComponent(team)}`, {
        method: "DELETE"
    });
}
async function triggerEscalation(body) {
    return apiFetch("/api/v1/escalate", {
        method: "POST",
        body: JSON.stringify(body)
    });
}
async function listEscalations(team) {
    const qs = team ? `?team=${encodeURIComponent(team)}` : "";
    return apiFetch(`/api/v1/escalations${qs}`);
}
async function sendNotification(body) {
    return apiFetch("/api/v1/notify", {
        method: "POST",
        body: JSON.stringify(body)
    });
}
async function getServicesHealth() {
    return apiFetch("/api/services/health");
}
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "AppSidebar",
    ()=>AppSidebar
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/next@16.1.6_react-dom@19.2.3_react@19.2.3__react@19.2.3/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/next@16.1.6_react-dom@19.2.3_react@19.2.3__react@19.2.3/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/next@16.1.6_react-dom@19.2.3_react@19.2.3__react@19.2.3/node_modules/next/dist/client/app-dir/link.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/next@16.1.6_react-dom@19.2.3_react@19.2.3__react@19.2.3/node_modules/next/navigation.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$2d$themes$40$0$2e$4$2e$6_react$2d$dom_e1ec481706e606e7e4324a4b413dee80$2f$node_modules$2f$next$2d$themes$2f$dist$2f$index$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/next-themes@0.4.6_react-dom_e1ec481706e606e7e4324a4b413dee80/node_modules/next-themes/dist/index.mjs [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$lib$2f$utils$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/lib/utils.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$lib$2f$api$2d$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/lib/api-client.ts [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$triangle$2d$alert$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__AlertTriangle$3e$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/lucide-react@0.544.0_react@19.2.3/node_modules/lucide-react/dist/esm/icons/triangle-alert.js [app-client] (ecmascript) <export default as AlertTriangle>");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$layout$2d$dashboard$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__LayoutDashboard$3e$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/lucide-react@0.544.0_react@19.2.3/node_modules/lucide-react/dist/esm/icons/layout-dashboard.js [app-client] (ecmascript) <export default as LayoutDashboard>");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$calendar$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Calendar$3e$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/lucide-react@0.544.0_react@19.2.3/node_modules/lucide-react/dist/esm/icons/calendar.js [app-client] (ecmascript) <export default as Calendar>");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$chart$2d$column$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__BarChart3$3e$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/lucide-react@0.544.0_react@19.2.3/node_modules/lucide-react/dist/esm/icons/chart-column.js [app-client] (ecmascript) <export default as BarChart3>");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$bell$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Bell$3e$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/lucide-react@0.544.0_react@19.2.3/node_modules/lucide-react/dist/esm/icons/bell.js [app-client] (ecmascript) <export default as Bell>");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$activity$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Activity$3e$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/lucide-react@0.544.0_react@19.2.3/node_modules/lucide-react/dist/esm/icons/activity.js [app-client] (ecmascript) <export default as Activity>");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$sun$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Sun$3e$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/lucide-react@0.544.0_react@19.2.3/node_modules/lucide-react/dist/esm/icons/sun.js [app-client] (ecmascript) <export default as Sun>");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$moon$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Moon$3e$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/lucide-react@0.544.0_react@19.2.3/node_modules/lucide-react/dist/esm/icons/moon.js [app-client] (ecmascript) <export default as Moon>");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$zap$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Zap$3e$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/lucide-react@0.544.0_react@19.2.3/node_modules/lucide-react/dist/esm/icons/zap.js [app-client] (ecmascript) <export default as Zap>");
;
var _s = __turbopack_context__.k.signature();
"use client";
;
;
;
;
;
;
;
const navItems = [
    {
        href: "/",
        label: "Dashboard",
        icon: __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$layout$2d$dashboard$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__LayoutDashboard$3e$__["LayoutDashboard"]
    },
    {
        href: "/incidents",
        label: "Incidents",
        icon: __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$triangle$2d$alert$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__AlertTriangle$3e$__["AlertTriangle"]
    },
    {
        href: "/alerts",
        label: "Alerts",
        icon: __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$zap$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Zap$3e$__["Zap"]
    },
    {
        href: "/oncall",
        label: "On-Call",
        icon: __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$calendar$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Calendar$3e$__["Calendar"]
    },
    {
        href: "/metrics-page",
        label: "SRE Metrics",
        icon: __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$chart$2d$column$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__BarChart3$3e$__["BarChart3"]
    },
    {
        href: "/notifications",
        label: "Notifications",
        icon: __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$bell$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Bell$3e$__["Bell"]
    }
];
const SERVICE_MAP = {
    "alert-ingestion": {
        name: "Alert Ingestion",
        port: 8001
    },
    "incident-management": {
        name: "Incident Mgmt",
        port: 8002
    },
    "oncall-service": {
        name: "On-Call Service",
        port: 8003
    },
    "notification-service": {
        name: "Notification",
        port: 8004
    }
};
function AppSidebar() {
    _s();
    const pathname = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["usePathname"])();
    const { theme, setTheme } = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$2d$themes$40$0$2e$4$2e$6_react$2d$dom_e1ec481706e606e7e4324a4b413dee80$2f$node_modules$2f$next$2d$themes$2f$dist$2f$index$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useTheme"])();
    const [health, setHealth] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "AppSidebar.useEffect": ()=>{
            let mounted = true;
            async function poll() {
                try {
                    const h = await (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$lib$2f$api$2d$client$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["getServicesHealth"])();
                    if (mounted) setHealth(h);
                } catch  {
                // ignore – show unknown state
                }
            }
            poll();
            const id = setInterval(poll, 30000);
            return ({
                "AppSidebar.useEffect": ()=>{
                    mounted = false;
                    clearInterval(id);
                }
            })["AppSidebar.useEffect"];
        }
    }["AppSidebar.useEffect"], []);
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("aside", {
        className: "flex h-screen w-64 flex-col border-r border-border bg-card",
        children: [
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "flex items-center gap-3 border-b border-border px-6 py-5",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "flex h-8 w-8 items-center justify-center rounded-lg bg-primary",
                        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$activity$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Activity$3e$__["Activity"], {
                            className: "h-4 w-4 text-primary-foreground"
                        }, void 0, false, {
                            fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                            lineNumber: 63,
                            columnNumber: 11
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                        lineNumber: 62,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                                className: "text-sm font-semibold text-foreground",
                                children: "Incident Platform"
                            }, void 0, false, {
                                fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                                lineNumber: 66,
                                columnNumber: 11
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                className: "text-xs text-muted-foreground",
                                children: "On-Call & SRE"
                            }, void 0, false, {
                                fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                                lineNumber: 67,
                                columnNumber: 11
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                        lineNumber: 65,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                lineNumber: 61,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("nav", {
                className: "flex-1 px-3 py-4",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("ul", {
                    className: "flex flex-col gap-1",
                    children: navItems.map((item)=>{
                        const isActive = pathname === item.href || item.href !== "/" && pathname.startsWith(item.href);
                        return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("li", {
                            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$client$2f$app$2d$dir$2f$link$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["default"], {
                                href: item.href,
                                className: (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$lib$2f$utils$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["cn"])("flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors", isActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-secondary hover:text-foreground"),
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(item.icon, {
                                        className: "h-4 w-4"
                                    }, void 0, false, {
                                        fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                                        lineNumber: 89,
                                        columnNumber: 19
                                    }, this),
                                    item.label
                                ]
                            }, void 0, true, {
                                fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                                lineNumber: 80,
                                columnNumber: 17
                            }, this)
                        }, item.href, false, {
                            fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                            lineNumber: 79,
                            columnNumber: 15
                        }, this);
                    })
                }, void 0, false, {
                    fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                    lineNumber: 73,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                lineNumber: 72,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "border-t border-border px-4 py-3",
                children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("button", {
                    onClick: ()=>setTheme(theme === "dark" ? "light" : "dark"),
                    className: "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground",
                    children: [
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$sun$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Sun$3e$__["Sun"], {
                            className: "h-4 w-4 rotate-0 scale-100 transition-transform dark:-rotate-90 dark:scale-0"
                        }, void 0, false, {
                            fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                            lineNumber: 104,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$lucide$2d$react$40$0$2e$544$2e$0_react$40$19$2e$2$2e$3$2f$node_modules$2f$lucide$2d$react$2f$dist$2f$esm$2f$icons$2f$moon$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__$3c$export__default__as__Moon$3e$__["Moon"], {
                            className: "absolute h-4 w-4 rotate-90 scale-0 transition-transform dark:rotate-0 dark:scale-100"
                        }, void 0, false, {
                            fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                            lineNumber: 105,
                            columnNumber: 11
                        }, this),
                        /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                            className: "ml-4",
                            children: "Toggle theme"
                        }, void 0, false, {
                            fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                            lineNumber: 106,
                            columnNumber: 11
                        }, this)
                    ]
                }, void 0, true, {
                    fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                    lineNumber: 100,
                    columnNumber: 9
                }, this)
            }, void 0, false, {
                fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                lineNumber: 99,
                columnNumber: 7
            }, this),
            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                className: "border-t border-border px-4 py-4",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                        className: "mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground",
                        children: "Services"
                    }, void 0, false, {
                        fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                        lineNumber: 112,
                        columnNumber: 9
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        className: "flex flex-col gap-1.5",
                        children: Object.entries(SERVICE_MAP).map(([key, svc])=>{
                            const status = health?.[key]?.status;
                            return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                className: "flex items-center gap-2 text-xs",
                                children: [
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$lib$2f$utils$2e$ts__$5b$app$2d$client$5d$__$28$ecmascript$29$__["cn"])("h-1.5 w-1.5 rounded-full", status === "up" ? "bg-green-500" : status === "down" ? "bg-destructive" : "bg-muted-foreground/40")
                                    }, void 0, false, {
                                        fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                                        lineNumber: 120,
                                        columnNumber: 17
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "text-muted-foreground",
                                        children: svc.name
                                    }, void 0, false, {
                                        fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                                        lineNumber: 130,
                                        columnNumber: 17
                                    }, this),
                                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])("span", {
                                        className: "ml-auto font-mono text-muted-foreground",
                                        children: [
                                            ":",
                                            svc.port
                                        ]
                                    }, void 0, true, {
                                        fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                                        lineNumber: 131,
                                        columnNumber: 17
                                    }, this)
                                ]
                            }, key, true, {
                                fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                                lineNumber: 119,
                                columnNumber: 15
                            }, this);
                        })
                    }, void 0, false, {
                        fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                        lineNumber: 115,
                        columnNumber: 9
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
                lineNumber: 111,
                columnNumber: 7
            }, this)
        ]
    }, void 0, true, {
        fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/app-sidebar.tsx",
        lineNumber: 59,
        columnNumber: 5
    }, this);
}
_s(AppSidebar, "C/+tPtF0a3JbV52EQ1EyQxJKsb8=", false, function() {
    return [
        __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["usePathname"],
        __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$2d$themes$40$0$2e$4$2e$6_react$2d$dom_e1ec481706e606e7e4324a4b413dee80$2f$node_modules$2f$next$2d$themes$2f$dist$2f$index$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useTheme"]
    ];
});
_c = AppSidebar;
var _c;
__turbopack_context__.k.register(_c, "AppSidebar");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
"[project]/Hackathon-os/incident-platform/services/web-ui/components/theme-provider.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "ThemeProvider",
    ()=>ThemeProvider
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/next@16.1.6_react-dom@19.2.3_react@19.2.3__react@19.2.3/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$2d$themes$40$0$2e$4$2e$6_react$2d$dom_e1ec481706e606e7e4324a4b413dee80$2f$node_modules$2f$next$2d$themes$2f$dist$2f$index$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Hackathon-os/incident-platform/services/web-ui/node_modules/.pnpm/next-themes@0.4.6_react-dom_e1ec481706e606e7e4324a4b413dee80/node_modules/next-themes/dist/index.mjs [app-client] (ecmascript)");
'use client';
;
;
function ThemeProvider({ children, ...props }) {
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$40$16$2e$1$2e$6_react$2d$dom$40$19$2e$2$2e$3_react$40$19$2e$2$2e$3_$5f$react$40$19$2e$2$2e$3$2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(__TURBOPACK__imported__module__$5b$project$5d2f$Hackathon$2d$os$2f$incident$2d$platform$2f$services$2f$web$2d$ui$2f$node_modules$2f2e$pnpm$2f$next$2d$themes$40$0$2e$4$2e$6_react$2d$dom_e1ec481706e606e7e4324a4b413dee80$2f$node_modules$2f$next$2d$themes$2f$dist$2f$index$2e$mjs__$5b$app$2d$client$5d$__$28$ecmascript$29$__["ThemeProvider"], {
        ...props,
        children: children
    }, void 0, false, {
        fileName: "[project]/Hackathon-os/incident-platform/services/web-ui/components/theme-provider.tsx",
        lineNumber: 10,
        columnNumber: 10
    }, this);
}
_c = ThemeProvider;
var _c;
__turbopack_context__.k.register(_c, "ThemeProvider");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
]);

//# sourceMappingURL=Hackathon-os_incident-platform_services_web-ui_b8e0ad52._.js.map