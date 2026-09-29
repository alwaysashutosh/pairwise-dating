import { NextRequest, NextResponse } from 'next/server';

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const base = (process.env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
  const target = `${base}/api/${path.join('/')}${request.nextUrl.search}`;
  const headers = new Headers();
  const contentType = request.headers.get('content-type');
  if (contentType) headers.set('content-type', contentType);
  const response = await fetch(target, { method: request.method, headers,
    body: ['GET', 'HEAD'].includes(request.method) ? undefined : await request.arrayBuffer(), cache: 'no-store' });
  return new NextResponse(response.body, { status: response.status, headers: { 'content-type': response.headers.get('content-type') || 'application/json' } });
}

export const GET = proxy;
export const POST = proxy;
