'use client';
import {useEffect,useState} from 'react';
import {Moon,Sun} from 'lucide-react';
export default function ThemeToggle(){
 const [light,setLight]=useState(false);
 useEffect(()=>{setLight(document.documentElement.dataset.theme==='light');},[]);
 function toggle(){const next=!light;setLight(next);document.documentElement.dataset.theme=next?'light':'dark';try{localStorage.setItem('repopilot:theme',next?'light':'dark')}catch{/* Theme remains usable without storage. */}}
 return <button type="button" className="theme-toggle" onClick={toggle} aria-label={light?'Switch to dark theme':'Switch to light theme'} title={light?'Switch to dark theme':'Switch to light theme'}>{light?<Moon size={18}/>:<Sun size={18}/>}</button>;
}
