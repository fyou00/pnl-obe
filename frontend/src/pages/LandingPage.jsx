import ClosingFooterSection from '../components/landing/ClosingFooterSection.jsx';
import ContextStripSection from '../components/landing/ContextStripSection.jsx';
import HeroSection from '../components/landing/HeroSection.jsx';
import MeasurementFlowSection from '../components/landing/MeasurementFlowSection.jsx';
import PrinciplesSection from '../components/landing/PrinciplesSection.jsx';
import RolesSection from '../components/landing/RolesSection.jsx';

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-[#FAF8F3] text-[#15333A]">
      <HeroSection />
      <ContextStripSection />
      <MeasurementFlowSection />
      <PrinciplesSection />
      <RolesSection />
      <ClosingFooterSection />
    </main>
  );
}
