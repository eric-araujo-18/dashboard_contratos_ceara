import Link from "next/link";

import Header from "../components/layout/Header";
import Footer from "../components/layout/Footer";

export default function NotFound() {
  return (
    <>
      <Header />

      <main className="flex min-h-[70vh] flex-col items-center justify-center gap-4 px-6 pt-20 text-center">
        <p className="font-mono text-sm font-bold text-[#006b47]">404</p>
        <h1 className="text-3xl font-bold text-[#131b2e]">Página não encontrada</h1>
        <p className="max-w-md text-[#49607e]">
          O endereço que você acessou não existe ou foi movido.
        </p>
        <Link
          href="/"
          className="mt-2 rounded-xl bg-[#006b47] px-5 py-3 font-semibold text-white hover:bg-[#005235]"
        >
          Voltar para o início
        </Link>
      </main>

      <Footer />
    </>
  );
}