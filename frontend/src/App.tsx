import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import Leaderboards from "./pages/Leaderboards";
import Teams from "./pages/Teams";
import TeamDetail from "./pages/TeamDetail";
import Matchup from "./pages/Matchup";
import GameDetail from "./pages/GameDetail";
import PlayoffBracket from "./pages/PlayoffBracket";
import PlayerDetail from "./pages/PlayerDetail";
import { ThemeProvider } from "./context/theme";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/leaderboards" element={<Leaderboards />} />
          <Route path="/teams" element={<Teams />} />
          <Route path="/matchup" element={<Matchup />} />
          <Route path="/game/:gameId" element={<GameDetail />} />
          <Route path="/playoffs" element={<PlayoffBracket />} />
          <Route path="/team/:id" element={<TeamDetail />} />
          <Route path="/player/:id" element={<PlayerDetail />} />

        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;

