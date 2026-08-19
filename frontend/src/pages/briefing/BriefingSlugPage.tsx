import { useParams } from "react-router"
import { countryByCode } from "@/lib/briefingCatalog"
import CountryBriefingPage from "./CountryBriefingPage"
import TopicBriefingPage from "./TopicBriefingPage"

export default function BriefingSlugPage() {
  const { slug } = useParams()
  const country = countryByCode(slug)
  if (country) return <CountryBriefingPage code={country.code} />
  return <TopicBriefingPage slug={slug} />
}
