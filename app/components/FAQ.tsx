"use client";

import React, { useState } from "react";

interface FAQItem {
  id: string;
  question: string;
  answer: string;
}

const FAQS: FAQItem[] = [
  {
    id: "faq-1",
    question: "How does Varve connect with DataHub?",
    answer:
      "Varve uses DataHub's native OpenAPI and GraphQL APIs to traverse lineage graphs, entity URNs, ownership metadata, and schema aspects without requiring invasive agent installations.",
  },
  {
    id: "faq-2",
    question: "What are the Evidence Tiers (Org-Validated vs Industry-General)?",
    answer:
      "Org-Validated findings are proven by joining against your team's real historical incident logs. Industry-General findings apply published post-mortem base rates for new teams or cold-start models with zero incident history.",
  },
  {
    id: "faq-3",
    question: "How does the append-only verification ledger work?",
    answer:
      "Every risk evaluation, severity change, and DataHub write-back emits a hash-chained audit record into SQLite/PostgreSQL. Running `verify_ledger.py` verifies the SHA-256 chain from block 0 to present.",
  },
  {
    id: "faq-4",
    question: "Are LLMs used for deterministic decision logic?",
    answer:
      "No. Risk correlation, incident joins, and severity assignments are executed with 100% deterministic SQL logic. LLMs are strictly isolated to formatting clean natural language summaries.",
  },
];

export default function FAQ() {
  const [openId, setOpenId] = useState<string | null>("faq-1");

  const toggleFAQ = (id: string) => {
    setOpenId(openId === id ? null : id);
  };

  return (
    <section id="faq" className="relative w-full max-w-7xl mx-auto px-6 py-20 border-t border-zinc-900">
      {/* Section Header */}
      <div className="flex flex-col items-center text-center space-y-4 mb-16">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold tracking-wider text-[#9B7FF6] uppercase border border-[#9B7FF6]/25 bg-gradient-to-b from-[#9B7FF6]/15 via-zinc-900/60 to-zinc-950/80 backdrop-blur-md">
          <span>Questions &amp; Answers</span>
        </div>
        <h2 className="text-3xl font-extrabold text-white sm:text-4xl lg:text-5xl tracking-tight">
          Frequently Asked Questions
        </h2>
        <p className="text-zinc-400 max-w-2xl text-sm sm:text-base leading-relaxed">
          Everything you need to know about Varve&apos;s DataHub integration, evidence tiers, and audit ledger.
        </p>
      </div>

      {/* Accordion List */}
      <div className="max-w-3xl mx-auto space-y-4">
        {FAQS.map((faq) => {
          const isOpen = openId === faq.id;

          return (
            <div
              key={faq.id}
              className="rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/80 via-zinc-900/40 to-zinc-950/90 backdrop-blur-xl overflow-hidden transition-all"
            >
              <button
                onClick={() => toggleFAQ(faq.id)}
                className="w-full p-6 text-left flex items-center justify-between gap-4 cursor-pointer select-none"
              >
                <span className="text-base font-bold text-white leading-snug">
                  {faq.question}
                </span>
                <span
                  className={`text-[#9B7FF6] font-mono text-xl transition-transform ${isOpen ? "rotate-45" : ""
                    }`}
                >
                  +
                </span>
              </button>

              {isOpen && (
                <div className="px-6 pb-6 text-sm text-zinc-400 leading-relaxed border-t border-zinc-800/60 pt-4">
                  {faq.answer}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
