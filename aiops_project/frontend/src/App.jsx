import React from "react";
import DeploymentGuide from "./DeploymentGuide";
import { Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import Contact from "./pages/Contact";
import NavBar from "./components/NavBar";
import Services from "./pages/Services";
import AuthPage from "./pages/AuthPage";
function App() {
  return <div className="min-h-screen overflow-x-hidden bg-slate-100 text-zinc-950 antialiased">
    <NavBar />
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route path="/contact" element={<Contact />} />
      <Route path="/deployment-guide" element={<DeploymentGuide />} />
      <Route path="/services" element={<Services />} />
    </Routes>
  </div>
}

export default App;
