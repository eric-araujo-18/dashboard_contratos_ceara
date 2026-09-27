import Header from "../components/layout/Header";
import Footer from "../components/layout/Footer";

import Hero from "../components/sections/Hero";
import DashboardPreview from "../components/sections/DashboardPreview";
import Objectives from "../components/sections/Objectives";
import Methodology from "../components/sections/Methodology";
import Technologies from "../components/sections/Technologies";
import Author from "../components/sections/Author";

export default function Home() {
  return (
    <>
      <Header />

      <main className="pt-20">
        <Hero />

        <Objectives />

        <DashboardPreview />

        <Methodology />

        <Technologies />

        <Author />
      </main>

      <Footer />
    </>
  );
}