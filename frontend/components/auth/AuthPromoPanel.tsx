import { Headset } from "lucide-react";
import Image from "next/image";

interface FeatureCard {
  icon: React.ReactNode;
  title: string;
  description: string;
}

interface AuthPromoPanelProps {
  headingDark: string;
  headingBlue: string;
  description: string;
  features: FeatureCard[];
}

export default function AuthPromoPanel({
  headingDark,
  headingBlue,
  description,
  features,
}: AuthPromoPanelProps) {
  return (
    <div className="relative hidden w-[45%] overflow-hidden bg-gradient-to-br from-blue-50 via-blue-50/80 to-slate-50 lg:flex lg:flex-col lg:justify-between">
      {/* Building background image — covers full panel */}
      <div className="absolute inset-0 pointer-events-none">
        <Image
          src="/assets/building.png"
          alt="SMIU Campus"
          fill
          className="object-cover object-bottom"
          sizes="(max-width: 1024px) 0vw, 45vw"
          priority
        />
        {/* Gradient overlays for readability */}
        <div className="absolute inset-0 bg-gradient-to-b from-blue-50/90 via-blue-50/40 to-blue-50/80" />
        <div className="absolute inset-0 bg-gradient-to-r from-blue-50/30 to-transparent" />
      </div>

      {/* Content */}
      <div className="relative z-10 p-10 lg:p-12">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="relative h-12 w-12 flex-shrink-0">
            <Image
              src="/assets/logo.png"
              alt="SMIU Logo"
              fill
              className="object-contain"
              sizes="48px"
              priority
            />
          </div>
          <div>
            <div className="text-xl font-bold tracking-tight text-secondary">SMIU</div>
            <div className="text-xs text-text-secondary">Sindh Madressatul Islam University</div>
          </div>
        </div>

        {/* Heading */}
        <h1 className="mt-10 text-4xl font-bold leading-tight tracking-tight lg:text-5xl">
          <span className="text-secondary">{headingDark}</span>{" "}
          <span className="text-primary">{headingBlue}</span>
        </h1>
        <p className="mt-4 max-w-sm text-base leading-relaxed text-text-secondary">
          {description}
        </p>
      </div>

      {/* Feature cards */}
      <div className="relative z-10 space-y-4 px-10 lg:px-12">
        {features.map((feature, i) => (
          <div
            key={i}
            className="flex items-start gap-3 rounded-xl border border-white/60 bg-white/70 p-4 shadow-sm backdrop-blur-sm"
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              {feature.icon}
            </div>
            <div>
              <div className="text-sm font-semibold text-secondary">{feature.title}</div>
              <div className="mt-0.5 text-xs leading-relaxed text-text-secondary">
                {feature.description}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Help section */}
      <div className="relative z-10 p-10 lg:p-12">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
            <Headset className="h-5 w-5 text-primary" />
          </div>
          <div>
            <div className="text-sm font-semibold text-secondary">Need Help?</div>
            <div className="text-xs text-text-secondary">
              Contact{" "}
              <a
                href="mailto:support@smiu.edu.pk"
                className="text-primary hover:underline"
              >
                support@smiu.edu.pk
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
