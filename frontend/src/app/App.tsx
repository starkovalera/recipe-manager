import { QueryClientProvider } from "@tanstack/react-query";

import { queryClient } from "./queryClient";

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <main className="app-shell">
        <header>
          <h1>Recipe Manager</h1>
        </header>
        <section>
          <p>Import recipes, review extracted sources, and edit saved recipes.</p>
        </section>
      </main>
    </QueryClientProvider>
  );
}
