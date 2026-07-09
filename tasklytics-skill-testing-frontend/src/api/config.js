const isDev = import.meta.env.DEV;

export const API_URL = isDev
  ? "http://localhost:8000"
  : "/api";



// export const API_URL =
//  import.meta.env.VITE_API_URL || "/api";