import { CallToAction } from "@/components/marketing/call-to-action";
import { FeaturedLocalities } from "@/components/marketing/featured-localities";
import { FindAccommodation } from "@/components/marketing/find-accommodation";
import { FindRoommate } from "@/components/marketing/find-roommate";
import { Hero } from "@/components/marketing/hero";
import { HowItWorks } from "@/components/marketing/how-it-works";
import { SiteFooter } from "@/components/marketing/site-footer";
import { SiteHeader } from "@/components/marketing/site-header";
import { Trust } from "@/components/marketing/trust";
import { SkipLink } from "@/components/ui/skip-link";
import { DISCOVERY_CANDIDATES } from "@/lib/mock/profiles";
import { FEATURED_LOCALITIES } from "@/lib/mock/societies";

/** The public landing page. */
export default function LandingPage() {
  const [heroPreview] = DISCOVERY_CANDIDATES;

  return (
    <>
      <SkipLink />
      <SiteHeader />
      <main id="main" className="flex-1">
        {heroPreview && <Hero preview={heroPreview} />}
        <HowItWorks />
        <FindRoommate />
        <FindAccommodation />
        <Trust />
        <FeaturedLocalities localities={FEATURED_LOCALITIES} />
        <CallToAction />
      </main>
      <SiteFooter />
    </>
  );
}
