import React, { Suspense, useEffect, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Environment, OrbitControls, useGLTF, useAnimations, GizmoHelper, GizmoViewport } from '@react-three/drei';
import * as THREE from 'three';
import { Physics, useBox, usePlane } from '@react-three/cannon';

// --------------------------------------------------------
// Background Scene Component
// --------------------------------------------------------
function BackgroundScene({ imagePath }) {
  if (!imagePath) return null;
  const url = imagePath.startsWith('http') || imagePath.startsWith('file://') || imagePath.startsWith('blob:')
    ? imagePath 
    : `file:///${imagePath.replace(/\\/g, '/')}`;
  return <Environment background files={url} />;
}

// --------------------------------------------------------
// Physics Floor
// --------------------------------------------------------
function Floor() {
  const [ref] = usePlane(() => ({ rotation: [-Math.PI / 2, 0, 0] }));
  return (
    <mesh ref={ref} receiveShadow>
      <planeGeometry args={[1000, 1000]} />
      <meshStandardMaterial color="#2f2f2f" opacity={0} transparent={true} />
    </mesh>
  );
}

// --------------------------------------------------------
// Physics Box (for interaction)
// --------------------------------------------------------
function PhysicsBox({ position, color, id, sceneObjectsRef }) {
  const [ref, api] = useBox(() => ({ mass: 1, position, args: [1, 1, 1] }));
  
  useEffect(() => {
    const unsub = api.position.subscribe(p => {
       if (sceneObjectsRef && sceneObjectsRef.current) {
          sceneObjectsRef.current[id] = { type: 'box', color, position: p };
       }
    });
    return unsub;
  }, [api.position, id, sceneObjectsRef, color]);

  return (
    <mesh ref={ref} castShadow receiveShadow>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color={color} />
    </mesh>
  );
}

// --------------------------------------------------------
// Avatar Component
// --------------------------------------------------------
function Avatar({ id, modelPath, position, animationTrigger, audioBase64, dynamicCode, destination, onReachDestination, manualOffset, manualRotation, avatarStatesRef }) {
  const group = useRef();
  
  const url = modelPath.startsWith('http') || modelPath.startsWith('file://') || modelPath.startsWith('blob:')
    ? modelPath : `file:///${modelPath.replace(/\\/g, '/')}`;

  const { scene, animations } = useGLTF(url);
  const { actions, mixer } = useAnimations(animations, scene);

  const [proceduralAnim, setProceduralAnim] = useState(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const originalY = position[1];

  // Kinematic Physics Body for the Avatar
  const [physicsRef, api] = useBox(() => ({
    type: 'Kinematic',
    mass: 1,
    position: [position[0], position[1] + 1, position[2]], // offset Y so it doesn't sink
    args: [1, 2, 1]
  }));

  const currentPos = useRef(new THREE.Vector3(position[0], position[1] + 1, position[2]));
  useEffect(() => {
    const unsub = api.position.subscribe(p => currentPos.current.set(p[0], p[1], p[2]));
    return unsub;
  }, [api.position]);

  const dynamicFuncRef = useRef(null);

  useEffect(() => {
    if (dynamicCode) {
      try {
        dynamicFuncRef.current = new Function('group', 'state', 'delta', 'THREE', 'api', dynamicCode);
      } catch (err) {
        dynamicFuncRef.current = null;
      }
    } else {
        dynamicFuncRef.current = null;
    }
  }, [dynamicCode]);

  useEffect(() => {
    if (audioBase64) {
      try {
        const audio = new Audio("data:audio/wav;base64," + audioBase64);
        setIsPlayingAudio(true);
        audio.play();
        audio.onended = () => setIsPlayingAudio(false);
      } catch (err) {}
    }
  }, [audioBase64]);

  useEffect(() => {
    if (actions && !animationTrigger && !destination) {
      const availableNames = Object.keys(actions);
      const idleMatch = availableNames.find(n => n.toLowerCase().includes('idle')) || availableNames[0];
      if (idleMatch && actions[idleMatch]) {
        mixer.stopAllAction();
        actions[idleMatch].reset().play();
      }
    }
  }, [actions, animationTrigger, destination, mixer]);

  useEffect(() => {
    // If moving to destination, force Walk if no trigger provided
    let trigger = animationTrigger;
    if (destination && !trigger) trigger = 'Walk';
    
    if (!trigger) return;
    
    const actionName = trigger.toLowerCase();
    let hasRealBones = false;

    if (actions) {
      const availableNames = Object.keys(actions);
      let match = availableNames.find(n => n.toLowerCase().includes(actionName));
      
      if (match && actions[match]) {
        hasRealBones = true;
        mixer.stopAllAction();
        const action = actions[match];
        action.reset().fadeIn(0.2).play();
        
        if (actionName !== 'idle' && !destination) {
           setTimeout(() => {
             const idleMatch = availableNames.find(n => n.toLowerCase().includes('idle')) || availableNames[0];
             if (idleMatch && actions[idleMatch]) {
                action.fadeOut(0.5);
                actions[idleMatch].reset().fadeIn(0.5).play();
             }
           }, 3000);
        }
      }
    }

    if (!hasRealBones && !destination) {
       setProceduralAnim(actionName);
       setTimeout(() => setProceduralAnim(null), 2000);
    }
  }, [animationTrigger, destination, actions, mixer]);

  useFrame((state, delta) => {
    if (!group.current) return;
    
    // Spatial Pathfinding (move_to logic)
    if (destination) {
       const target = new THREE.Vector3(...destination);
       target.y += 1; // offset Y for physics center
       
       const dist = new THREE.Vector2(currentPos.current.x, currentPos.current.z).distanceTo(new THREE.Vector2(target.x, target.z));
       if (dist > 0.1) {
           const nextPos = currentPos.current.clone().lerp(target, 0.05);
           api.position.set(nextPos.x, nextPos.y, nextPos.z);
           
           // Rotate towards target
           const dir = target.clone().sub(currentPos.current).normalize();
           const angle = Math.atan2(dir.x, dir.z);
           api.rotation.set(0, angle, 0);
       } else {
           if (onReachDestination) onReachDestination(id);
       }
       return; 
    }

    if (dynamicFuncRef.current) {
      try {
        dynamicFuncRef.current(group.current, state, delta, THREE, api);
      } catch (err) {}
      return; 
    }

    if (isPlayingAudio && !proceduralAnim) {
       group.current.scale.setScalar(1 + Math.sin(state.clock.elapsedTime * 15) * 0.02);
    } else {
       group.current.scale.setScalar(1);
    }

    if (proceduralAnim === 'jump') {
       api.position.set(currentPos.current.x, originalY + 1 + Math.abs(Math.sin(state.clock.elapsedTime * 10)) * 2, currentPos.current.z);
    } else if (proceduralAnim === 'wave') {
       group.current.rotation.z = Math.sin(state.clock.elapsedTime * 10) * 0.5;
    } else if (proceduralAnim === 'walk' || proceduralAnim === 'run') {
       group.current.rotation.y = Math.sin(state.clock.elapsedTime * 5) * 0.5;
       api.position.set(currentPos.current.x, currentPos.current.y, currentPos.current.z + Math.cos(state.clock.elapsedTime * 5) * 0.05);
    } else if (proceduralAnim === 'dance') {
       group.current.rotation.y = state.clock.elapsedTime * 5;
       api.position.set(currentPos.current.x, originalY + 1 + Math.abs(Math.sin(state.clock.elapsedTime * 15)) * 1, currentPos.current.z);
       group.current.scale.setScalar(1 + Math.sin(state.clock.elapsedTime * 20) * 0.2);
    } else {
       group.current.rotation.z = THREE.MathUtils.lerp(group.current.rotation.z, 0, 0.1);
    }

    // Sync state for backend spatial awareness
    if (avatarStatesRef && avatarStatesRef.current) {
        avatarStatesRef.current[`Avatar ${id + 1}`] = {
            position: [currentPos.current.x, currentPos.current.y, currentPos.current.z]
        };
    }
  });

  return (
    <group ref={physicsRef}>
      <group 
        position={[manualOffset?.x || 0, (manualOffset?.y || 0) - 1, manualOffset?.z || 0]}
        rotation={[manualRotation?.x || 0, manualRotation?.y || 0, manualRotation?.z || 0]}
      >
        <group ref={group} dispose={null}>
          <primitive object={scene} />
        </group>
      </group>
    </group>
  );
}

// --------------------------------------------------------
// Main Web3DScene Canvas
// --------------------------------------------------------
export default function Web3DScene({ backgroundPath, avatars, showGrid = true, manualOffset, sceneOffset, manualRotation, sceneRotation, onReachDestination, avatarStatesRef, sceneObjectsRef }) {
  return (
    <Canvas camera={{ position: [0, 2, 8], fov: 50 }} style={{width: '100%', height: '100%', borderRadius: '12px', background: '#1a1a2e'}}>
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} intensity={1.5} />
      <directionalLight position={[-10, 10, -5]} intensity={0.5} />
      
      <group 
        position={[sceneOffset?.x || 0, sceneOffset?.y || 0, sceneOffset?.z || 0]}
        rotation={[sceneRotation?.x || 0, sceneRotation?.y || 0, sceneRotation?.z || 0]}
      >
        <Physics>
          <Floor />
          <PhysicsBox position={[2, 5, 2]} color="orange" id="box_orange" sceneObjectsRef={sceneObjectsRef} />
          <PhysicsBox position={[-2, 10, 3]} color="red" id="box_red" sceneObjectsRef={sceneObjectsRef} />
          <PhysicsBox position={[0, 8, -3]} color="cyan" id="box_cyan" sceneObjectsRef={sceneObjectsRef} />

          <Suspense fallback={null}>
            <BackgroundScene imagePath={backgroundPath} />
            
            {avatars.map((avatar, idx) => (
              <Avatar 
                key={idx} 
                id={idx}
                modelPath={avatar.path} 
                position={[avatar.positionX, 0, 0]} 
                animationTrigger={avatar.trigger}
                audioBase64={avatar.audioBase64}
                dynamicCode={avatar.dynamicCode}
                destination={avatar.destination}
                manualOffset={manualOffset}
                manualRotation={manualRotation}
                onReachDestination={onReachDestination}
                avatarStatesRef={avatarStatesRef}
              />
            ))}
          </Suspense>
        </Physics>

        <axesHelper args={[50]} />
        <GizmoHelper alignment="top-right" margin={[80, 80]}>
          <GizmoViewport axisColors={['#ff3653', '#8adb00', '#2c8fdf']} labelColor="white" />
        </GizmoHelper>

        {showGrid && (
          <gridHelper args={[1000, 1000, '#4f4f4f', '#2f2f2f']} position={[0, 0, 0]} />
        )}
      </group>

      <OrbitControls makeDefault minPolarAngle={0} maxPolarAngle={Math.PI / 1.5} />
    </Canvas>
  );
}
