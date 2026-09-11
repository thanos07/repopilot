import {cpSync,rmSync} from 'node:fs';
rmSync('out',{recursive:true,force:true});
cpSync('frontend/out','out',{recursive:true});
