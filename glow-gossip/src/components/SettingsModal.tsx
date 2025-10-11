import { Settings, Moon, Sun, Type } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from './ui/dialog';
import { Button } from './ui/button';
import { Switch } from './ui/switch';
import { Label } from './ui/label';
import { Slider } from './ui/slider';

interface SettingsModalProps {
  emotionDetection: boolean;
  onEmotionDetectionChange: (enabled: boolean) => void;
  textSize: number;
  onTextSizeChange: (size: number) => void;
  darkMode: boolean;
  onDarkModeChange: (enabled: boolean) => void;
}

export const SettingsModal = ({
  emotionDetection,
  onEmotionDetectionChange,
  textSize,
  onTextSizeChange,
  darkMode,
  onDarkModeChange,
}: SettingsModalProps) => {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button size="icon" variant="secondary" className="fixed top-4 left-4 z-50 glow-primary">
          <Settings className="w-5 h-5" />
        </Button>
      </DialogTrigger>
      <DialogContent className="glass-effect border-primary/30">
        <DialogHeader>
          <DialogTitle className="text-2xl font-bold">Settings</DialogTitle>
          <DialogDescription>
            Customize your coding assistant experience
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* Emotion Detection Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label htmlFor="emotion-detection" className="text-base font-medium">
                Emotion Detection
              </Label>
              <p className="text-sm text-muted-foreground">
                Enable webcam-based emotion awareness
              </p>
            </div>
            <Switch
              id="emotion-detection"
              checked={emotionDetection}
              onCheckedChange={onEmotionDetectionChange}
            />
          </div>

          {/* Dark Mode Toggle */}
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label htmlFor="dark-mode" className="text-base font-medium flex items-center gap-2">
                {darkMode ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
                Theme
              </Label>
              <p className="text-sm text-muted-foreground">
                {darkMode ? 'Dark' : 'Light'} mode
              </p>
            </div>
            <Switch
              id="dark-mode"
              checked={darkMode}
              onCheckedChange={onDarkModeChange}
            />
          </div>

          {/* Text Size Slider */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Type className="w-4 h-4" />
              <Label htmlFor="text-size" className="text-base font-medium">
                Text Size
              </Label>
            </div>
            <Slider
              id="text-size"
              min={12}
              max={20}
              step={1}
              value={[textSize]}
              onValueChange={(value) => onTextSizeChange(value[0])}
              className="w-full"
            />
            <p className="text-sm text-muted-foreground">
              Current size: {textSize}px
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
