import axios from "axios";

export const http = axios.create({
  baseURL: "/api/v1",
  withCredentials: true, // если останетесь на cookie-сессии
});
