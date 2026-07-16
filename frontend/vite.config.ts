import react from "@vitejs/plugin-react";
import { defineConfig, type Plugin } from "vite";

function recipeClientLogPlugin(): Plugin {
  return {
    name: "recipe-client-log",
    configureServer(server) {
      server.middlewares.use("/_recipes_client_log", (request, response) => {
        if (request.method !== "POST") {
          response.statusCode = 405;
          response.end();
          return;
        }
        let body = "";
        request.on("data", (chunk) => {
          body += chunk;
        });
        request.on("end", () => {
          try {
            const payload = JSON.parse(body);
            const meta = payload.meta ? ` ${JSON.stringify(payload.meta)}` : "";
            server.config.logger.info(`${payload.message}${meta}`);
          } catch {
            server.config.logger.info("[recipes.frontend.api] malformed client log");
          }
          response.statusCode = 204;
          response.end();
        });
      });
    },
  };
}

export default defineConfig({
  plugins: [recipeClientLogPlugin(), react()],
  server: {
    host: "127.0.0.1",
  },
  test: {
    environment: "jsdom",
    globals: true
  }
});
