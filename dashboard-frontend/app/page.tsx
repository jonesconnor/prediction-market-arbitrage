import { getOpportunities } from "@/lib/api"
import { DashboardClient } from "@/components/dashboard-client"

export const dynamic = "force-dynamic"

export default async function Page() {
  let initialData

  try {
    initialData = await getOpportunities()
  } catch (error) {
    console.error("Failed to fetch initial opportunities:", error)
    initialData = []
  }

  return <DashboardClient initialData={initialData} />
}
