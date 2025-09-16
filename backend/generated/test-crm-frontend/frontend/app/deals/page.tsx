import { getDeals } from '../lib/api'
import { Card } from '../components/Card'
import { Pill } from '../components/Pill'
import { Target, DollarSign, Calendar } from 'lucide-react'

export default async function DealsPage() {
  let deals = []
  
  try {
    deals = await getDeals()
  } catch (error) {
    console.error('Failed to fetch deals:', error)
  }

  const getStageColor = (stage: string) => {
    switch (stage) {
      case 'prospecting':
        return 'bg-blue-100 text-blue-800'
      case 'negotiation':
        return 'bg-yellow-100 text-yellow-800'
      case 'closed_won':
        return 'bg-green-100 text-green-800'
      case 'closed_lost':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Deals</h1>
        <p className="mt-2 text-gray-600">Track your sales opportunities</p>
      </div>

      <div className="grid gap-4">
        {deals.map((deal) => (
          <Card key={deal.id} className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Target className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">{deal.name}</h3>
                  <p className="text-sm text-gray-600">{deal.description}</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">
                    {formatCurrency(deal.amount)}
                  </p>
                  <p className="text-sm text-gray-600">Value</p>
                </div>
                <Pill className={getStageColor(deal.stage)}>
                  {deal.stage.replace('_', ' ').toUpperCase()}
                </Pill>
                <div className="text-right text-sm text-gray-500">
                  <div className="flex items-center space-x-1">
                    <Calendar className="w-4 h-4" />
                    <span>{new Date(deal.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {deals.length === 0 && (
        <Card className="p-8 text-center">
          <Target className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No deals found</h3>
          <p className="text-gray-600">Get started by creating your first deal.</p>
        </Card>
      )}
    </div>
  )
}
