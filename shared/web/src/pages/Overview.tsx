import { useEffect, useState } from "react";
import { fetchGroupState } from "../api/client";
import { ModeBadge } from "../components/ModeBadge";

export function OverviewPage() {
  const [tag, setTag] = useState("A-SIM");
  const [color, setColor] = useState("blue");
  const [mode, setMode] = useState("SIM");

  useEffect(() => {
    fetchGroupState("A")
      .then((state) => {
        setMode(state.mode);
        setTag(state.mode_badge.tag);
        setColor(state.mode_badge.color);
      })
      .catch(() => {
        setMode("SIM");
        setTag("A-SIM");
        setColor("blue");
      });
  }, []);

  return (
    <section>
      <h1>Overview</h1>
      <p>
        Mode <ModeBadge mode={mode} color={color} tag={tag} />
      </p>
      <p>Capital hierarchy, activity, and attention flags load from scoped read APIs.</p>
    </section>
  );
}
