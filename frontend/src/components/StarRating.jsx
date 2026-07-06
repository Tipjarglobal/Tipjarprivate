import React, { useState } from "react";
import { Star } from "lucide-react";

// The Apex Scale — 1 to 10 stars, color shifts white -> volt as it fills.
export default function StarRating({ value = 0, onRate, size = 22, readOnly = false }) {
  const [hover, setHover] = useState(0);
  const active = hover || value;

  return (
    <div className="flex items-center gap-0.5" data-testid="apex-scale">
      {Array.from({ length: 10 }).map((_, i) => {
        const idx = i + 1;
        const filled = idx <= active;
        const color = active >= 8 ? "#E1FF00" : active >= 5 ? "#CCEE00" : "#FFFFFF";
        return (
          <button
            key={idx}
            type="button"
            data-testid={`apex-star-${idx}`}
            disabled={readOnly}
            onMouseEnter={() => !readOnly && setHover(idx)}
            onMouseLeave={() => !readOnly && setHover(0)}
            onClick={() => !readOnly && onRate && onRate(idx)}
            className={`transition-transform ${readOnly ? "cursor-default" : "hover:scale-125 cursor-pointer"}`}
            style={{ lineHeight: 0 }}
          >
            <Star
              size={size}
              strokeWidth={1.5}
              fill={filled ? color : "transparent"}
              color={filled ? color : "#52525b"}
              style={filled ? { filter: `drop-shadow(0 0 4px ${color}aa)` } : {}}
            />
          </button>
        );
      })}
    </div>
  );
}
