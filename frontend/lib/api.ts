export const API = process.env.NEXT_PUBLIC_API_URL || '';
export type Person = { id:string; name:string; linkedin_url:string|null; instagram_url:string|null; source_type:string; simulation_mode:string; simulation_notice:string|null; ingestion_status:string; profession:string|null; profile_summary:string; profile:{profession:string|null; education:string|null; interests:string[]; hobbies:string[]; lifestyle:string[]; conversation_topics:string[]; preferences:string[]; summary:string; analysis:Record<string,unknown>}|null };
export type Ranking = { person:Person; score:number; dimensions:Record<string,number>; reason:string; strengths:string[]; differences:string[]; date_id:number };
export type MatchDate = { id:number; status:string; person_a:Person; person_b:Person; messages:{turn_number:number; agent_person_id:string; speaker:string; message:string}[]; compatibility:{overall_score:number; dimensions:Record<string,number>; strengths:string[]; differences:string[]; reason:string; simulation_mode:string; activity:{event:string; message:string; turn_number?:number}[]}; summary:string };
async function request<T>(path:string, init?:RequestInit):Promise<T>{ const response=await fetch(`${API}${path}`,{...init,headers:{'Content-Type':'application/json',...init?.headers},cache:'no-store'}); if(!response.ok) throw new Error((await response.json()).detail||'Request failed'); return response.json(); }
export const getPeople=()=>request<Person[]>('/api/people');
export const getStats=()=>request<{people:number;agents:number;dates:number;rankings:number}>('/api/stats');
export const getPerson=(id:string)=>request<Person>(`/api/people/${id}`);
export const getRankings=(id:string)=>request<Ranking[]>(`/api/rankings/${id}`);
export const getDate=(id:string)=>request<MatchDate>(`/api/dates/${id}`);
export const createDate=(a:string,b:string)=>request<{id:number}>('/api/dates',{method:'POST',body:JSON.stringify({person_a_id:a,person_b_id:b})});
export const analyzeProfile=(data:{linkedin_url?:string;instagram_url?:string;name?:string})=>request<Person>('/api/people/analyze',{method:'POST',body:JSON.stringify(data)});
