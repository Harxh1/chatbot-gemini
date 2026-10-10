import axios from "axios";

// In dev, Vite proxies /api to http://localhost:8080 (see vite.config.js).
const http = axios.create({ baseURL: "/api" });

/** Drop empty values so blank filters are not sent as ?state=&course= */
function clean(params) {
  return Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== "" && v !== null && v !== undefined)
  );
}

export const fetchColleges = (params) =>
  http.get("/colleges", { params: clean(params) }).then((r) => r.data);

export const fetchStates = () => http.get("/meta/states").then((r) => r.data);

export const fetchCourses = () => http.get("/meta/courses").then((r) => r.data);

export const fetchRecommendations = (body) =>
  http.post("/recommendations", clean(body)).then((r) => r.data);

export const fetchAiRecommendations = (body) =>
  http.post("/recommendations/ai", clean(body)).then((r) => r.data);

export const sendChat = (messages) => http.post("/chat", { messages }).then((r) => r.data);
