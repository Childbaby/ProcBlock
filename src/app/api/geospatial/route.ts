import { NextResponse } from 'next/server'

// Django runs on 8000; ai-service defaults to 8001 to avoid the conflict.
const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8001'

export async function GET() {
  try {
    const response = await fetch(`${AI_SERVICE_URL}/geospatial`, {
      cache: 'no-store',
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: 'AI service unavailable' },
        { status: 502 }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Geospatial API error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch geospatial data' },
      { status: 500 }
    )
  }
}
