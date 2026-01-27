import { Card, CardContent, CardHeader } from "@/components/ui/card"

export function LoadingSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i} className="animate-pulse">
          <CardHeader className="h-16 bg-muted/50 rounded-t-lg" />
          <CardContent className="h-24 bg-muted/20" />
        </Card>
      ))}
    </div>
  )
}

export function ViewSkeleton() {
    return (
        <div className="space-y-6 h-full flex flex-col p-6">
            <div className="h-8 w-1/3 bg-muted/50 rounded animate-pulse" />
            <div className="grid gap-6 md:grid-cols-3 flex-1">
                <div className="md:col-span-2 h-full bg-muted/20 rounded-lg animate-pulse" />
                <div className="h-full bg-muted/20 rounded-lg animate-pulse" />
            </div>
        </div>
    )
}
