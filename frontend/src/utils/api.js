const BASE_URL = "http://localhost:8000";

export async function authFetch(endpoint, options = {}) {
  const token = localStorage.getItem("token");
  console.log("Token: ", token); // is it still present?
  const isFormData = options.body instanceof FormData;

  const res = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      "Authorization": `Bearer ${token}`,
      ...options.headers,
    },
  });

  if (res.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.href = "/auth";
  }

  return res;
}