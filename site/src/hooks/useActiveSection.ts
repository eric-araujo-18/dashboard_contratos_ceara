"use client";

import { useEffect, useState } from "react";

export function useActiveSection(sectionIds: string[]) {
  const [activeSection, setActiveSection] = useState(
    sectionIds[0] ?? ""
  );

  useEffect(() => {
    const updateActiveSection = () => {
      // Altura aproximada do Header + margem
      const offset = 140;

      let currentSection = sectionIds[0] ?? "";

      for (const id of sectionIds) {
        const element = document.getElementById(id);

        if (!element) {
          continue;
        }

        const sectionTop =
          element.getBoundingClientRect().top +
          window.scrollY;

        if (window.scrollY + offset >= sectionTop) {
          currentSection = id;
        }
      }

      setActiveSection(currentSection);
    };

    // Executa assim que o componente carrega
    updateActiveSection();

    window.addEventListener(
      "scroll",
      updateActiveSection,
      { passive: true }
    );

    window.addEventListener(
      "resize",
      updateActiveSection
    );

    return () => {
      window.removeEventListener(
        "scroll",
        updateActiveSection
      );

      window.removeEventListener(
        "resize",
        updateActiveSection
      );
    };
  }, [sectionIds]);

  return activeSection;
}